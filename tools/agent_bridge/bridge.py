"""Claude <-> Codex bridge: one persistent peer session per caller session, run as the real interactive CLI.

The caller's own session id comes from the environment the agent CLI sets for its shell tools:
CLAUDE_CODE_SESSION_ID (Claude Code) or CODEX_THREAD_ID (Codex).

- The first `ask` from a caller session starts the peer CLI interactively (`codex` / `claude --session-id`)
  inside a tmux session (socket `agent-bridge`) and opens a Terminator window attached to it.
- Later asks from the same caller session (also after it was closed and resumed) go to the SAME peer
  session: pasted into the CLI if it is still open, otherwise the CLI is reopened with
  `codex resume <id>` / `claude --resume <id>`.
- The answer is read from the peer's own transcript (Codex rollout / Claude project jsonl). Each message
  carries a tag `⟦bridge <nonce>⟧` so a turn the user typed by hand is never mistaken for the reply.

State: ${XDG_STATE_HOME:-~/.local/state}/os_ai_agent/bridge/pairs.json (mode 0600).
"""
import argparse
import datetime as dt
import fcntl
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

PEERS = ('claude', 'codex')
CALLER_ENV = {'claude': 'CLAUDE_CODE_SESSION_ID', 'codex': 'CODEX_THREAD_ID'}
# Variables that identify an agent session; never leak the caller's into the peer.
SESSION_VARS = ('CLAUDE_CODE_SESSION_ID', 'CLAUDECODE', 'CLAUDE_CODE_ENTRYPOINT', 'CLAUDE_CODE_CHILD_SESSION',
                'CLAUDE_CODE_MESSAGING_SOCKET', 'CLAUDE_CODE_MESSAGING_TOKEN', 'CLAUDE_PID',
                'CLAUDE_CODE_SESSION_ATTENDED', 'CLAUDE_CODE_CHILD_NOTES_DIR', 'CODEX_COMPANION_SESSION_ID',
                'CODEX_COMPANION_TRANSCRIPT_PATH', 'CODEX_THREAD_ID', 'CODEX_SESSION_ID', 'CODEX_TOOL_CALL_ID',
                # these point at the caller's terminal pane, not the peer's
                'TERMINATOR_UUID', 'TERMINATOR_DBUS_NAME', 'TERMINATOR_DBUS_PATH', 'TMUX', 'TMUX_PANE')
ID_RE = re.compile(r'^[0-9A-Za-z][0-9A-Za-z_-]{7,63}$')
CLAUDE_READ_TOOLS = 'Read,Grep,Glob,Bash(git diff:*),Bash(git status:*),Bash(git log:*),Bash(git show:*)'
CLAUDE_EDIT_TOOLS = 'Edit,Write,NotebookEdit'
POLL = 0.5


class BridgeError(Exception):
    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.code = code


def other(agent):
    return 'codex' if agent == 'claude' else 'claude'


def now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


# ---------- state ----------

def state_dir():
    base = os.environ.get('XDG_STATE_HOME') or os.path.join(os.path.expanduser('~'), '.local', 'state')
    d = Path(base) / 'os_ai_agent' / 'bridge'
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(d, 0o700)
    return d


@contextmanager
def locked(path, blocking=True):
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            raise BridgeError('another ask for this session pair is still running; wait for it to finish', 3)
        yield
    finally:
        os.close(fd)


def load_pairs(d):
    p = d / 'pairs.json'
    try:
        return json.loads(p.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise BridgeError(f'{p} is corrupt ({e}); fix or remove it')


def update_pair(d, key, **fields):
    with locked(d / 'pairs.lock'):
        pairs = load_pairs(d)
        pairs.setdefault(key, {}).update(fields)
        tmp = d / 'pairs.json.tmp'
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as f:
            json.dump(pairs, f, indent=2, sort_keys=True)
        os.replace(tmp, d / 'pairs.json')
        return pairs[key]


def get_pair(d, key):
    with locked(d / 'pairs.lock'):
        return dict(load_pairs(d).get(key, {}))


def peer_of(d, agent, sid):
    """The pair key for which session `sid` of `agent` is the peer, if any."""
    for k, v in load_pairs(d).items():
        if v.get('peer') == agent and sid in (v.get('peer_id'), v.get('pending_id')):
            return k
    return None


def pair_key(caller, sid, to):
    return f'{caller}:{sid}->{to}'


def caller_identity(to, override=None):
    caller = other(to)
    sid = (override or os.environ.get(CALLER_ENV[caller], '')).strip()
    if not sid:
        raise BridgeError(f'{CALLER_ENV[caller]} is not set: run this from inside a {caller} session '
                          f'(or pass --caller-session ID)', 2)
    if not ID_RE.match(sid):
        raise BridgeError(f'invalid session id: {sid!r}', 2)
    return caller, sid


# ---------- tmux + window ----------

def tmux_cmd(*args):
    return [os.environ.get('AGENT_BRIDGE_TMUX_BIN', 'tmux'), '-L',
            os.environ.get('AGENT_BRIDGE_TMUX_SOCKET', 'agent-bridge'), *args]


def tmux(*args, input=None, check=True):
    p = subprocess.run(tmux_cmd(*args), input=input, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise BridgeError(f'tmux {args[0]} failed: {p.stderr.strip()}', 4)
    return p


def tmux_name(caller, sid, to):
    return f'{caller}-{sid}-to-{to}'   # full id: UUIDv7 ids created close together share a prefix


def tmux_alive(name):
    return tmux('has-session', '-t', f'={name}', check=False).returncode == 0


def title_for(caller, sid, to, peer_id):
    return f'{caller.capitalize()} {sid[:8]} ⇄ {to.capitalize()} {(peer_id or "new")[:8]}'


def tmux_start(name, cwd, argv, title):
    # No marker variable for the peer: Codex runs tool commands in a shared app-server daemon that outlives the
    # CLI which started it, so any variable set here would leak into every later Codex session.
    # Nested calls are refused by pair state instead (see peer_of).
    env_wrap = ['env', *[a for v in SESSION_VARS for a in ('-u', v)], 'AGENT_BRIDGE_DEPTH=']
    tmux('new-session', '-d', '-s', name, '-c', cwd, '-x', '200', '-y', '50', '--', *env_wrap, *argv)
    for opt in (('status-left-length', '90'), ('status-left', f' {title} '), ('status-right', ''),
                ('window-status-format', ''), ('window-status-current-format', '')):
        tmux('set-option', '-t', f'={name}:', *opt, check=False)   # -t is a target pane: needs the ':'


def tmux_paste(name, text):
    tmux('load-buffer', '-b', name, '-', input=text)
    tmux('paste-buffer', '-p', '-d', '-b', name, '-t', f'={name}:')
    time.sleep(0.5)                       # let the TUI finish the bracketed paste before submitting
    tmux('send-keys', '-t', f'={name}:', 'Enter')


TERM_VARS = ('TERMINATOR_UUID', 'TERMINATOR_DBUS_NAME', 'TERMINATOR_DBUS_PATH')


def _cmdline(pid):
    try:
        return [a.decode(errors='replace') for a in Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0') if a]
    except OSError:
        return []


def _environ(pid):
    try:
        raw = Path(f'/proc/{pid}/environ').read_bytes()
    except OSError:
        return {}
    return dict(kv.decode(errors='replace').split('=', 1) for kv in raw.split(b'\0') if b'=' in kv)


def _ancestors():
    pid, out = os.getppid(), []
    for _ in range(30):
        if pid <= 1:
            break
        out.append(_cmdline(pid))
        try:
            pid = int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    return out


def codex_tui_terminal(thread_id, cwd):
    """Terminal vars of the interactive Codex CLI showing `thread_id`.

    The CLI runs tool commands in a shared app-server daemon, so our own environment says nothing about the
    caller's terminal. Look at the `codex` TUI processes instead: one started on this thread
    (`codex resume <id>`), else the only one running in the same directory. Ambiguous -> None (new window).
    """
    exact, same_dir = [], []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        args = _cmdline(proc.name)
        if not args or os.path.basename(args[0]) != 'codex' or any(
                a in ('app-server', 'exec', 'queue', 'mcp-server') for a in args[1:3]):
            continue
        env = _environ(proc.name)
        if not env.get('TERMINATOR_UUID') or env.get('TERM_PROGRAM') == 'vscode':
            continue
        term = {k: env[k] for k in TERM_VARS if k in env}
        if thread_id and thread_id in args:
            exact.append(term)
            continue
        try:
            if os.path.realpath(f'/proc/{proc.name}/cwd') == os.path.realpath(cwd):
                same_dir.append(term)
        except OSError:
            pass
    for found in (exact, same_dir):
        uuids = {t['TERMINATOR_UUID'] for t in found}
        if len(uuids) == 1:
            return found[0]
        if len(uuids) > 1:
            return None
    return None


def caller_terminal():
    """Terminator vars of the caller's terminal, or None when it is not (reliably) a Terminator terminal."""
    if os.environ.get('TERM_PROGRAM') == 'vscode' or os.environ.get('AGENT_BRIDGE_LAYOUT') == 'window':
        return None
    anc = _ancestors()
    daemon = next((a for a in anc if 'app-server' in a), None)
    if daemon is None:
        env = {k: os.environ[k] for k in TERM_VARS if k in os.environ}
        return env if env.get('TERMINATOR_UUID') else None
    if any('.vscode' in x or 'chatgpt' in x for x in daemon[:1]):
        return None                       # Codex in VS Code / the desktop app: no terminal of its own
    return codex_tui_terminal(os.environ.get('CODEX_THREAD_ID'), os.getcwd())


def split_caller_terminal(name):
    """If the caller runs inside a Terminator terminal, split it so both CLIs sit side by side.
    Returns a status string, or None to fall back to a new window."""
    term = caller_terminal()
    remotinator = shutil.which('remotinator')
    if not term or not remotinator:
        return None
    env = {k: v for k, v in os.environ.items() if k not in TERM_VARS}
    env.update(term)                      # talk to the caller's Terminator instance
    try:
        r = subprocess.run([remotinator, 'vsplit', '-u', term['TERMINATOR_UUID'],
                            '-x', shlex.join(tmux_cmd('attach-session', '-t', f'={name}'))],
                           capture_output=True, text=True, timeout=10, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0 or 'rror' in (r.stdout + r.stderr):
        return None
    return 'opened side by side in your Terminator window'


def open_window(name, title, force=False):
    """Open a Terminator window attached to the tmux session, unless one is already attached."""
    attach = 'tmux -L ' + os.environ.get('AGENT_BRIDGE_TMUX_SOCKET', 'agent-bridge') + f' attach -t {name}'
    if os.environ.get('AGENT_BRIDGE_NO_WINDOW'):
        return f'window disabled (attach: {attach})'
    if not force and tmux('list-clients', '-t', f'={name}', '-F', '#{client_name}', check=False).stdout.strip():
        return 'window already open'
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        return f'no display (attach: {attach})'
    split = split_caller_terminal(name)
    if split:
        return split
    term = shutil.which('terminator')
    if not term:
        return f'terminator not installed (attach: {attach})'
    subprocess.Popen([term, '-u', '-T', title, '-x', *tmux_cmd('attach-session', '-t', f'={name}')],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return 'window opened'


# ---------- peer CLIs ----------

def peer_argv(to, peer_id, new_id, cwd, write, prompt):
    """Interactive CLI command; prompt=None opens the session without sending anything."""
    tail = [] if prompt is None else [prompt]
    if to == 'codex':
        exe = os.environ.get('AGENT_BRIDGE_CODEX_BIN', 'codex')
        flags = ['-s', 'workspace-write' if write else 'read-only', '-a', 'on-request', '-C', cwd]
        return [exe, 'resume', *flags, '--', peer_id, *tail] if peer_id else [exe, *flags, '--', *tail]
    exe = os.environ.get('AGENT_BRIDGE_CLAUDE_BIN', 'claude')
    perm = ['--permission-mode', 'acceptEdits'] if write else \
        ['--permission-mode', 'default', f'--allowedTools={CLAUDE_READ_TOOLS}',
         f'--disallowedTools={CLAUDE_EDIT_TOOLS}']
    sess = ['--resume', peer_id] if peer_id else ['--session-id', new_id]
    return [exe, *sess, *perm, '--', *tail]


def codex_home():
    return Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')


def claude_home():
    return Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude')


def codex_transcript(tid):
    files = sorted((codex_home() / 'sessions').glob(f'*/*/*/rollout-*-{tid}.jsonl'), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def claude_transcript(sid):
    files = sorted((claude_home() / 'projects').glob(f'*/{sid}.jsonl'), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def find_new_codex_thread(nonce, since, cwd):
    """The rollout whose own session_meta has our cwd and whose USER message carries the nonce."""
    for p in (codex_home() / 'sessions').glob('*/*/*/rollout-*.jsonl'):
        try:
            if p.stat().st_mtime < since - 2:
                continue
            text = p.read_text(errors='replace')
        except OSError:
            continue
        if nonce not in text:
            continue
        meta, hit = None, False
        for line in text.splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            pl = e.get('payload') or {}
            if e.get('type') == 'session_meta' and meta is None:
                meta = pl
            elif e.get('type') == 'event_msg' and pl.get('type') == 'user_message' and nonce in str(pl.get('message', '')):
                hit = True
                break
        if hit and meta and meta.get('cwd') in (None, cwd) and ID_RE.match(str(meta.get('id', ''))):
            return meta['id']
    return None


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') in ('text', 'input_text'))
    return ''


class CodexTurn:
    """Feed rollout events; done when the turn that carries the nonce completes."""
    def __init__(self, nonce):
        self.nonce, self.seen, self.answer, self.error = nonce, False, None, None
        self.current_turn = self.my_turn = None

    def feed(self, e):
        p = e.get('payload') or {}
        kind = p.get('type') if e.get('type') == 'event_msg' else None
        if kind == 'task_started':
            self.current_turn = p.get('turn_id')
        elif not self.seen and (
                (kind == 'user_message' and self.nonce in str(p.get('message', ''))) or
                (e.get('type') == 'response_item' and p.get('type') == 'message' and p.get('role') == 'user'
                 and self.nonce in _text_of(p.get('content')))):
            self.seen, self.my_turn = True, self.current_turn
        elif self.seen and kind in ('task_complete', 'turn_aborted'):
            if self.my_turn and p.get('turn_id') != self.my_turn:
                return False              # another turn ended (e.g. one the user typed)
            if kind == 'task_complete':
                self.answer = p.get('last_agent_message') or ''
            else:
                self.error = 'turn aborted in Codex'
        return self.answer is not None or self.error is not None


def _events(path):
    try:
        with open(path, errors='replace') as f:
            for line in f:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def codex_idle(path):
    """True when no turn is in flight (every task_started has ended)."""
    open_turns = 0
    for e in _events(path):
        kind = (e.get('payload') or {}).get('type') if e.get('type') == 'event_msg' else None
        if kind == 'task_started':
            open_turns += 1
        elif kind in ('task_complete', 'turn_aborted') and open_turns:
            open_turns -= 1
    return open_turns == 0


def claude_idle(path, quiet=3):
    """True when the turn is over: the system turn summary came last, or an interrupt, or an end_turn entry
    and the transcript has been quiet for `quiet` s (one message is written as several end_turn entries)."""
    last = None
    for e in _events(path):
        if e.get('type') in ('user', 'assistant') or (
                e.get('type') == 'system' and e.get('subtype') in ClaudeTurn.END_MARKERS):
            last = e
    if last is None:
        return True
    if last['type'] == 'system':
        return True
    msg = last.get('message') if isinstance(last.get('message'), dict) else {}
    if last['type'] == 'assistant':
        return msg.get('stop_reason') == 'end_turn' and time.time() - path.stat().st_mtime > quiet
    return '[Request interrupted by user' in _text_of(msg.get('content'))


class ClaudeTurn:
    """Claude writes one assistant message as several entries (thinking, text, ...), each carrying
    stop_reason=end_turn, so end_turn alone is not the end: the turn ends at the system summary entry
    (stop_hook_summary / turn_duration) after it, or when the transcript stays quiet (see settle())."""
    END_MARKERS = ('stop_hook_summary', 'turn_duration')

    def __init__(self, nonce):
        self.nonce, self.seen, self.texts, self.answer, self.error = nonce, False, [], None, None
        self.ended = False

    def settle(self):
        """Called when the transcript has been quiet for a while after end_turn."""
        if self.ended and self.answer is None:
            self.answer = '\n'.join(self.texts)
        return self.answer is not None

    def feed(self, e):
        msg = e.get('message') if isinstance(e.get('message'), dict) else {}
        if e.get('type') == 'system' and self.ended and e.get('subtype') in self.END_MARKERS:
            return self.settle()
        if e.get('type') == 'user':
            text = _text_of(msg.get('content'))
            if self.nonce in text:
                self.seen, self.texts, self.ended = True, [], False
            elif self.seen and '[Request interrupted by user' in text:
                self.error = 'interrupted in Claude'
            elif self.seen:
                self.texts, self.ended = [], False   # a tool result: the final answer comes after it
        elif self.seen and e.get('type') == 'assistant':
            self.texts += [c['text'] for c in msg.get('content', []) if isinstance(c, dict)
                           and c.get('type') == 'text' and c.get('text')]
            self.ended = msg.get('stop_reason') == 'end_turn'
        return self.answer is not None or self.error is not None


def screen_tail(name, n=8):
    p = tmux('capture-pane', '-p', '-t', f'={name}:', check=False)
    lines = [line.rstrip() for line in p.stdout.splitlines() if line.strip()]
    return '\n'.join('    | ' + line for line in lines[-n:])


def wait_turn(locate, turn, name, timeout, hint_after=20):
    """Tail the transcript found by locate() until `turn` is done, the CLI exits, or timeout."""
    turn.timed_out = False
    start = time.time()
    deadline, path, pos, buf, hinted = start + timeout, None, 0, '', False
    quiet_since = time.time()
    while time.time() < deadline:
        if not turn.seen and not hinted and time.time() - start > hint_after:
            hinted = True                 # e.g. a trust/login/update prompt only the user may answer
            print(f'[bridge] the {name} CLI has not taken the message yet; it may be waiting for the user '
                  f'in its window. Screen:\n{screen_tail(name)}', file=sys.stderr, flush=True)
        path = path or locate()
        if path:
            with open(path, errors='replace') as f:
                f.seek(pos)
                chunk = f.read()
                pos = f.tell()
            if chunk:
                buf, quiet_since = buf + chunk, time.time()
            *lines, buf = buf.split('\n')
            for line in lines:
                try:
                    if turn.feed(json.loads(line)):
                        return turn
                except (json.JSONDecodeError, AttributeError):
                    continue
            if hasattr(turn, 'settle') and time.time() - quiet_since > 3 and turn.settle():
                return turn
        if not tmux_alive(name):
            turn.error = turn.error or 'the peer CLI exited before answering'
            return turn
        time.sleep(POLL)
    turn.timed_out = True
    turn.error = f'no answer within {timeout}s' + ('' if turn.seen else f'; screen:\n{screen_tail(name)}')
    return turn


# ---------- commands ----------

def transcript_of(to, peer_id):
    return codex_transcript(peer_id) if to == 'codex' else claude_transcript(peer_id)


def peer_ready(to, peer_id, pair):
    """Safe to paste: the CLI is past any startup dialog and no turn is running.

    Past the dialogs = it took our previous message, or (after `open`) the transcript grew since it was opened,
    i.e. the user already used it.
    """
    path = transcript_of(to, peer_id)
    if not path:
        return False
    last_nonce = pair.get('last_nonce')
    took_ours = bool(last_nonce) and last_nonce in path.read_text(errors='replace')
    used_since_open = pair.get('opened_size') is not None and path.stat().st_size > int(pair['opened_size'])
    if not (took_ours or used_since_open):
        return False
    return codex_idle(path) if to == 'codex' else claude_idle(path)


def cmd_ask(a):
    to = a.to
    caller, sid = caller_identity(to, a.caller_session)
    owner = peer_of(state_dir(), caller, sid)
    if owner:
        raise BridgeError(f'refusing nested bridge call: this {caller} session is itself the bridge peer of {owner} '
                          f'(it must not call back through the bridge)', 2)
    message = sys.stdin.read() if a.message == '-' else a.message
    if not message.strip():
        raise BridgeError('empty message', 2)
    mode = 'write' if a.write else 'read'

    d = state_dir()
    key, name = pair_key(caller, sid, to), tmux_name(caller, sid, to)
    with locked(d / f'{caller}-{sid}-to-{to}.lock', blocking=False):
        pair = get_pair(d, key)
        if a.new:
            if tmux_alive(name):
                tmux('kill-session', '-t', f'={name}', check=False)
            prev = pair.get('previous_peer_ids', []) + ([pair['peer_id']] if pair.get('peer_id') else [])
            # persist first, so a failed start can never fall back to the old session
            pair = update_pair(d, key, peer_id=None, pending_nonce=None, pending_id=None, previous_peer_ids=prev,
                               cwd=os.path.abspath(a.cwd))
        cwd = pair.get('cwd') or os.path.abspath(a.cwd)
        if not os.path.isdir(cwd):
            raise BridgeError(f'peer working directory no longer exists: {cwd} (use --new)', 2)
        peer_id = pair.get('peer_id')

        def record(**fields):
            nonlocal pair
            pair = update_pair(d, key, peer=to, cwd=cwd, tmux=name, last=now(),
                               created=pair.get('created') or now(), **fields)

        alive = tmux_alive(name)
        if not peer_id and (pair.get('pending_nonce') or pair.get('pending_id')):
            # a previous first ask ended before the session id was recorded (trust prompt, timeout, reboot)
            if to == 'codex':
                peer_id = find_new_codex_thread(pair['pending_nonce'], 0, cwd) if pair.get('pending_nonce') else None
            elif claude_transcript(pair['pending_id']):
                peer_id = pair['pending_id']
            if peer_id:
                record(peer_id=peer_id, pending_nonce=None, pending_id=None)
        if alive and not peer_id:
            raise BridgeError(f'the {to} CLI in tmux session {name} has not started its session yet (answer any '
                              f'prompt in its window), or use --new. Screen:\n{screen_tail(name)}', 3)
        if alive and not peer_ready(to, peer_id, pair):
            raise BridgeError(f'the {to} CLI is busy (working, or waiting for the user in its window); not pasting '
                              f'into it. Try again when it is idle. Screen:\n{screen_tail(name)}', 3)
        if alive and pair.get('mode', 'read') != mode:
            tmux('kill-session', '-t', f'={name}', check=False)   # idle: restart it in the requested mode
            alive = False

        nonce = uuid.uuid4().hex[:10]
        tagged = f'{message.rstrip()}\n\n⟦bridge {nonce}⟧'
        new_id = str(uuid.uuid4())
        title = title_for(caller, sid, to, peer_id or (new_id if to == 'claude' else None))
        started = time.time()
        # Persist what we are about to send BEFORE sending, so `wait` can always find it, even if this
        # process is killed right after the paste. Roll back if sending fails.
        before = {k: pair.get(k) for k in ('last_nonce', 'asked', 'pending_nonce', 'pending_id', 'mode', 'opened_size')}
        pending = {} if peer_id else ({'pending_nonce': nonce} if to == 'codex' else {'pending_id': new_id})
        record(last_nonce=nonce, asked=now(), opened_size=None,
               **({} if alive else {'mode': mode}), **pending)
        try:
            if alive:
                tmux_paste(name, tagged)
                how = 'sent to the open CLI'
            else:
                tmux_start(name, cwd, peer_argv(to, peer_id, new_id, cwd, a.write, tagged), title)
                how = f'reopened {to} session' if peer_id else f'started a new {to} session'
        except BaseException:
            record(**before)
            raise
        window = open_window(name, title)
        print(f'[bridge] {caller} {sid} → {to} {peer_id or "(new)"} ({how}; {window})', file=sys.stderr, flush=True)
        peer_id, turn = collect(d, key, name, to, nonce, started, a.wait)
    return finish(to, turn)


EX_STILL_RUNNING = 75   # EX_TEMPFAIL: the peer is still working; call `wait`


def collect(d, key, name, to, nonce, started, budget):
    """Wait (up to `budget` s) for the answer to the ask tagged `nonce`. Safe to call again after a cut-off."""
    deadline = started + budget
    pair = get_pair(d, key)
    peer_id = pair.get('peer_id')
    while not peer_id:                    # first ask: learn the new session id
        if to == 'codex' and pair.get('pending_nonce'):
            peer_id = find_new_codex_thread(pair['pending_nonce'], 0, pair.get('cwd'))
        elif to == 'claude' and pair.get('pending_id') and claude_transcript(pair['pending_id']):
            peer_id = pair['pending_id']
        if peer_id:
            update_pair(d, key, peer_id=peer_id, pending_nonce=None, pending_id=None)
            break
        if not tmux_alive(name):
            t = ClaudeTurn(nonce) if to == 'claude' else CodexTurn(nonce)
            t.timed_out, t.error = False, f'the {to} CLI exited before starting its session'
            return None, t
        if time.time() >= deadline:
            t = ClaudeTurn(nonce) if to == 'claude' else CodexTurn(nonce)
            t.timed_out, t.error = True, f'{to} has not started its session yet; screen:\n{screen_tail(name)}'
            return None, t
        time.sleep(POLL)
    locate = (lambda: codex_transcript(peer_id)) if to == 'codex' else (lambda: claude_transcript(peer_id))
    turn = wait_turn(locate, CodexTurn(nonce) if to == 'codex' else ClaudeTurn(nonce), name,
                     max(1, deadline - time.time()))
    update_pair(d, key, last=now())
    return peer_id, turn


def finish(to, turn):
    if turn.answer is not None:
        print(turn.answer)
        return 0
    if turn.timed_out:
        if not turn.seen:
            print(f'agent-bridge: {to} has NOT taken the message yet. It may be waiting for the USER in its window '
                  f'(trust/login/update prompt): tell the user what the screen shows. Then run `bridge wait --to {to}`.'
                  f'\n{turn.error}', file=sys.stderr)
        else:
            print(f'agent-bridge: {to} is still working ({turn.error}). The answer is not lost: '
                  f'run `bridge wait --to {to}` to keep waiting.', file=sys.stderr)
        return EX_STILL_RUNNING
    raise BridgeError(f'{to} did not return an answer: {turn.error}', 4)


def cmd_wait(a):
    caller, sid = caller_identity(a.to, a.caller_session)
    d, key, name = state_dir(), pair_key(caller, sid, a.to), tmux_name(caller, sid, a.to)
    with locked(d / f'{caller}-{sid}-to-{a.to}.lock', blocking=False):
        nonce = get_pair(d, key).get('last_nonce')
        if not nonce:
            raise BridgeError('nothing to wait for: no ask has been sent in this pair', 2)
        _, turn = collect(d, key, name, a.to, nonce, time.time(), a.wait)
    return finish(a.to, turn)


def cmd_status(a):
    pairs = load_pairs(state_dir())
    mine = [pair_key(other(to), os.environ[CALLER_ENV[other(to)]], to)
            for to in PEERS if os.environ.get(CALLER_ENV[other(to)])]
    rows = pairs if a.all else {k: v for k, v in pairs.items() if k in mine}
    for v in rows.values():
        v['open'] = bool(v.get('tmux')) and tmux_alive(v['tmux'])
    if a.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    if not rows:
        print('no paired session for this caller' + ('' if mine else ' (not inside Claude/Codex)'))
        return 0
    for k, v in sorted(rows.items(), key=lambda kv: kv[1].get('last', '')):
        print(f'{k}\n  peer {v.get("peer")} {v.get("peer_id")} ({"CLI open" if v["open"] else "closed"})\n'
              f'  cwd  {v.get("cwd")}\n  last {v.get("last")}')
    return 0


def cmd_open(a):
    caller, sid = caller_identity(a.to, a.caller_session)
    d, key = state_dir(), pair_key(caller, sid, a.to)
    with locked(d / f'{caller}-{sid}-to-{a.to}.lock', blocking=False):
        pair = get_pair(d, key)
        if not pair.get('peer_id'):
            raise BridgeError('no paired session yet: ask something first', 2)
        name, title = tmux_name(caller, sid, a.to), title_for(caller, sid, a.to, pair['peer_id'])
        if not tmux_alive(name):
            tmux_start(name, pair['cwd'], peer_argv(a.to, pair['peer_id'], None, pair['cwd'], False, None), title)
            path = transcript_of(a.to, pair['peer_id'])
            # asks may paste only once the transcript grows (the user got past any startup dialog and used it)
            update_pair(d, key, mode='read', opened_size=path.stat().st_size if path else 0)
        print(open_window(name, title, force=True))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='agent-bridge', description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('ask', help='send a message to the paired peer session and print its final answer')
    p.add_argument('--to', choices=PEERS, required=True)
    p.add_argument('-m', '--message', required=True, help="message text, or '-' to read stdin")
    p.add_argument('--write', action='store_true',
                   help='allow the peer to edit files (default: read-only); applies when the CLI is (re)started')
    p.add_argument('--new', action='store_true', help='start a fresh peer session for this caller session')
    p.add_argument('--cwd', default='.', help='working directory for a NEW pair (default: current)')
    p.add_argument('--wait', '--timeout', dest='wait', type=int, default=1800,
                   help='seconds to wait for the answer (default 1800); on expiry exit 75 and continue with `wait`')
    p.add_argument('--caller-session', help='override the caller session id (default: from environment)')
    p.set_defaults(fn=cmd_ask)
    p = sub.add_parser('wait', help='keep waiting for the answer to the last ask of this pair (after exit 75 or a cut-off)')
    p.add_argument('--to', choices=PEERS, required=True)
    p.add_argument('--wait', '--timeout', dest='wait', type=int, default=1800)
    p.add_argument('--caller-session')
    p.set_defaults(fn=cmd_wait)
    p = sub.add_parser('status', help='show the peer session paired with this caller session')
    p.add_argument('--all', action='store_true')
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser('open', help='open the paired peer CLI in a Terminator window (resumes it if closed)')
    p.add_argument('--to', choices=PEERS, required=True)
    p.add_argument('--caller-session')
    p.set_defaults(fn=cmd_open)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except BridgeError as e:
        print(f'agent-bridge: {e}', file=sys.stderr)
        return e.code
