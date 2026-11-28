import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / 'scripts' / 'agent-bridge'
sys.path.insert(0, str(ROOT))
from tools.agent_bridge.bridge import ClaudeTurn, CodexTurn, peer_argv  # noqa: E402

# Fake interactive CLIs: write a transcript like the real ones, answer the argv prompt,
# then keep reading the terminal for pasted messages (bracketed paste ends with ESC[201~).
FAKE_COMMON = textwrap.dedent('''\
    import json, os, sys, uuid
    from pathlib import Path
    a = sys.argv[1:]
    with open(os.environ['FAKE_LOG'], 'a') as f:
        f.write(json.dumps({'argv': a, 'leak': [v for v in ('CLAUDE_CODE_SESSION_ID', 'CODEX_THREAD_ID') if v in os.environ],
                            'depth': os.environ.get('AGENT_BRIDGE_DEPTH')}) + '\\n')
    if os.environ.get('FAKE_FAIL'):
        sys.exit(1)
    prompt = a[a.index('--') + 1:]
    def first(m): return m.split('\\n')[0]
    def loop(answer):
        sys.stdout.write('\\x1b[?2004h'); sys.stdout.flush()   # enable bracketed paste, like real TUIs
        buf = []
        for line in sys.stdin:
            buf.append(line.replace('\\x1b[200~', '').replace('\\x1b[201~', ''))
            if '\\x1b[201~' in line:
                answer(''.join(buf).strip()); buf = []
''')

FAKE_CODEX = FAKE_COMMON + textwrap.dedent('''\
    if a[0] == 'resume':
        tid = prompt.pop(0)
    else:
        tid = str(uuid.uuid4())
    d = Path(os.environ['CODEX_HOME']) / 'sessions/2026/11/28'
    d.mkdir(parents=True, exist_ok=True)
    path = d / f'rollout-2026-11-28T00-00-00-{tid}.jsonl'
    def w(e):
        with open(path, 'a') as f: f.write(json.dumps(e) + '\\n')
    if a[0] != 'resume':
        w({'type': 'session_meta', 'payload': {'id': tid}})
    n = [0]
    def answer(m):
        n[0] += 1
        turn = f't{n[0]}'
        w({'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': turn}})
        w({'type': 'event_msg', 'payload': {'type': 'user_message', 'message': m}})
        if 'HANG' in m:
            return
        if 'SLOW' in m:
            import time; time.sleep(4)
        w({'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': turn, 'last_agent_message': 'codex says: ' + first(m)}})
    if prompt: answer(prompt[0])
    loop(answer)
''')

FAKE_CLAUDE = FAKE_COMMON + textwrap.dedent('''\
    sid = a[a.index('--resume') + 1] if '--resume' in a else a[a.index('--session-id') + 1]
    d = Path(os.environ['CLAUDE_CONFIG_DIR']) / 'projects/-fake'
    d.mkdir(parents=True, exist_ok=True)
    def w(e):
        with open(d / f'{sid}.jsonl', 'a') as f: f.write(json.dumps(e) + '\\n')
    def answer(m):
        w({'type': 'user', 'message': {'role': 'user', 'content': m}})
        w({'type': 'assistant', 'message': {'stop_reason': 'tool_use', 'content': [{'type': 'text', 'text': 'reading'}]}})
        w({'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'x'}]}})
        w({'type': 'assistant', 'message': {'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': 'claude says: ' + first(m)}]}})
    if prompt: answer(prompt[0])
    loop(answer)
''')


@unittest.skipUnless(shutil.which('tmux'), 'tmux not installed')
class BridgeTmuxTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.state, self.work, self.calls = t / 'state', t / 'work', t / 'calls.jsonl'
        self.work.mkdir()
        for name, body in (('codex', FAKE_CODEX), ('claude', FAKE_CLAUDE)):
            p = t / name
            p.write_text(f'#!{sys.executable}\n' + body)
            p.chmod(0o755)
        self.sock = 'ab-test-' + uuid.uuid4().hex[:8]
        base = {k: v for k, v in os.environ.items() if not k.startswith(('CLAUDE', 'CODEX', 'AGENT_BRIDGE', 'TMUX'))}
        self.env = dict(base, XDG_STATE_HOME=str(self.state), FAKE_LOG=str(self.calls),
                        CODEX_HOME=str(t / 'codexhome'), CLAUDE_CONFIG_DIR=str(t / 'claudehome'),
                        AGENT_BRIDGE_CODEX_BIN=str(t / 'codex'), AGENT_BRIDGE_CLAUDE_BIN=str(t / 'claude'),
                        AGENT_BRIDGE_TMUX_SOCKET=self.sock, AGENT_BRIDGE_NO_WINDOW='1')

    def tearDown(self):
        subprocess.run(['tmux', '-L', self.sock, 'kill-server'], capture_output=True)
        self.tmp.cleanup()

    def ask(self, to, msg, *extra, **env):
        return subprocess.run([sys.executable, str(BRIDGE), 'ask', '--to', to, '-m', msg, '--timeout', '20', *extra],
                              cwd=self.work, capture_output=True, text=True, env=dict(self.env, **env))

    def launches(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []

    def pairs(self):
        return json.loads((self.state / 'os_ai_agent/bridge/pairs.json').read_text())

    def kill(self, name):
        subprocess.run(['tmux', '-L', self.sock, 'kill-session', '-t', '=' + name], check=True)
        time.sleep(0.2)

    def test_claude_to_codex_paste_then_resume(self):
        C = dict(CLAUDE_CODE_SESSION_ID='claude-aaaa1111')
        r = self.ask('codex', 'first question', **C)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, 'codex says: first question'), r.stderr)
        tid = self.pairs()['claude:claude-aaaa1111->codex']['peer_id']
        r = self.ask('codex', 'second\nmulti-line', **C)          # CLI still open: pasted, no new launch
        self.assertEqual((r.returncode, r.stdout.strip()), (0, 'codex says: second'), r.stderr)
        self.assertEqual(len(self.launches()), 1)
        self.assertIn('sent to the open CLI', r.stderr)
        self.kill('claude-claude-aaaa1111-to-codex')                    # user closed the CLI / rebooted
        r = self.ask('codex', 'third', **C)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, 'codex says: third'), r.stderr)
        argv = self.launches()[-1]['argv']
        self.assertEqual(argv[0], 'resume')
        self.assertEqual(argv[argv.index('--') + 1], tid)
        self.assertEqual(self.pairs()['claude:claude-aaaa1111->codex']['peer_id'], tid)
        first = self.launches()[0]
        self.assertEqual((first['leak'], first['depth']), ([], '1'))
        self.assertIn('read-only', first['argv'])

    def test_codex_to_claude_session_id_then_resume(self):
        X = dict(CODEX_THREAD_ID='codex-cccc3333')
        r = self.ask('claude', 'review this', **X)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, 'claude says: review this'), r.stderr)
        argv = self.launches()[0]['argv']
        sid = argv[argv.index('--session-id') + 1]
        self.assertIn('--disallowedTools=Edit,Write,NotebookEdit', argv)
        self.kill('codex-codex-cccc3333-to-claude')
        r = self.ask('claude', 'again', **X)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, 'claude says: again'), r.stderr)
        argv = self.launches()[-1]['argv']
        self.assertEqual(argv[argv.index('--resume') + 1], sid)

    def test_different_caller_sessions_get_different_peers(self):
        self.ask('codex', 'a', CLAUDE_CODE_SESSION_ID='claude-aaaa1111')
        self.ask('codex', 'b', CLAUDE_CODE_SESSION_ID='claude-bbbb2222')
        p = self.pairs()
        self.assertNotEqual(p['claude:claude-aaaa1111->codex']['peer_id'], p['claude:claude-bbbb2222->codex']['peer_id'])

    def test_new_flag_starts_fresh_session(self):
        C = dict(CLAUDE_CODE_SESSION_ID='claude-aaaa1111')
        self.ask('codex', 'a', **C)
        old = self.pairs()['claude:claude-aaaa1111->codex']['peer_id']
        r = self.ask('codex', 'b', '--new', **C, FAKE_FAIL='1')     # failed fresh start: never back to old
        self.assertNotEqual(r.returncode, 0)
        self.assertIsNone(self.pairs()['claude:claude-aaaa1111->codex']['peer_id'])
        r = self.ask('codex', 'b', **C)
        self.assertEqual(r.returncode, 0, r.stderr)
        pair = self.pairs()['claude:claude-aaaa1111->codex']
        self.assertNotEqual(pair['peer_id'], old)
        self.assertEqual(pair['previous_peer_ids'], [old])

    def test_peer_exits_without_answer_records_nothing(self):
        r = self.ask('claude', 'a', CODEX_THREAD_ID='codex-cccc3333', FAKE_FAIL='1')
        self.assertEqual(r.returncode, 4)
        pair = self.pairs()['codex:codex-cccc3333->claude']
        self.assertIsNone(pair.get('peer_id'))       # only a pending id, never a recorded ghost session
        self.assertTrue(pair['pending_id'])

    def test_requires_caller_session_and_refuses_nesting(self):
        r = self.ask('codex', 'a')
        self.assertEqual(r.returncode, 2)
        self.assertIn('CLAUDE_CODE_SESSION_ID', r.stderr)
        r = self.ask('claude', 'a', CODEX_THREAD_ID='codex-cccc3333', AGENT_BRIDGE_DEPTH='1')
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.launches(), [])


    def test_busy_cli_is_not_pasted_into(self):
        C = dict(CLAUDE_CODE_SESSION_ID='claude-aaaa1111')
        r = self.ask('codex', 'HANG forever', '--timeout', '2', **C)
        self.assertEqual(r.returncode, 75)
        r = self.ask('codex', 'next', **C)
        self.assertEqual(r.returncode, 3)
        self.assertIn('busy', r.stderr)
        self.assertEqual(len(self.launches()), 1)

    def test_short_wait_then_wait_command_gets_the_answer(self):
        C = dict(CLAUDE_CODE_SESSION_ID='claude-aaaa1111')
        self.ask('codex', 'warm up', **C)
        r = self.ask('codex', 'SLOW job', '--wait', '1', **C)        # caller's tool would cut us off here
        self.assertEqual(r.returncode, 75, r.stderr)
        self.assertIn('bridge wait --to codex', r.stderr)
        w = subprocess.run([sys.executable, str(BRIDGE), 'wait', '--to', 'codex', '--wait', '20'], cwd=self.work,
                           capture_output=True, text=True, env=dict(self.env, **C))
        self.assertEqual((w.returncode, w.stdout.strip()), (0, 'codex says: SLOW job'), w.stderr)

    def test_bridge_killed_mid_wait_loses_nothing(self):
        C = dict(CLAUDE_CODE_SESSION_ID='claude-aaaa1111')
        self.ask('codex', 'warm up', **C)
        proc = subprocess.Popen([sys.executable, str(BRIDGE), 'ask', '--to', 'codex', '-m', 'SLOW killed'], cwd=self.work,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(self.env, **C))
        time.sleep(1.5)
        proc.terminate()                                          # e.g. the caller's tool timeout
        proc.communicate()
        w = subprocess.run([sys.executable, str(BRIDGE), 'wait', '--to', 'codex', '--wait', '20'], cwd=self.work,
                           capture_output=True, text=True, env=dict(self.env, **C))
        self.assertEqual((w.returncode, w.stdout.strip()), (0, 'codex says: SLOW killed'), w.stderr)

    def test_first_claude_ask_cut_off_is_recovered_by_wait(self):
        X = dict(CODEX_THREAD_ID='codex-cccc3333')
        r = self.ask('claude', 'hello', '--wait', '0', **X)
        self.assertIn(r.returncode, (0, 75), r.stderr)
        w = subprocess.run([sys.executable, str(BRIDGE), 'wait', '--to', 'claude', '--wait', '20'], cwd=self.work,
                           capture_output=True, text=True, env=dict(self.env, **X))
        self.assertEqual((w.returncode, w.stdout.strip()), (0, 'claude says: hello'), w.stderr)
        self.assertTrue(self.pairs()['codex:codex-cccc3333->claude']['peer_id'])

    def test_mode_change_restarts_idle_cli(self):
        C = dict(CLAUDE_CODE_SESSION_ID='claude-aaaa1111')
        self.ask('codex', 'a', **C)
        r = self.ask('codex', 'b', '--write', **C)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, 'codex says: b'), r.stderr)
        argv = self.launches()[-1]['argv']
        self.assertEqual((argv[0], 'workspace-write' in argv), ('resume', True))
        r = self.ask('codex', 'c', **C)                          # back to read-only: restarted again
        self.assertIn('read-only', self.launches()[-1]['argv'])
        self.assertEqual(len(self.launches()), 3)

    def test_session_ids_sharing_a_prefix_do_not_share_a_cli(self):
        self.ask('codex', 'a', CLAUDE_CODE_SESSION_ID='01a21fbc-0000-7000-8000-000000000001')
        r = self.ask('codex', 'b', CLAUDE_CODE_SESSION_ID='01a21fbc-0000-7000-8000-000000000002')
        self.assertIn('started a new codex session', r.stderr)
        self.assertEqual(len(self.launches()), 2)


class TurnParsingTest(unittest.TestCase):
    def test_codex_ignores_turns_without_nonce(self):
        t = CodexTurn('n1')
        self.assertFalse(t.feed({'type': 'event_msg', 'payload': {'type': 'user_message', 'message': 'typed by user'}}))
        self.assertFalse(t.feed({'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': 'no'}}))
        t.feed({'type': 'event_msg', 'payload': {'type': 'user_message', 'message': 'q ⟦bridge n1⟧'}})
        self.assertTrue(t.feed({'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': 'yes'}}))
        self.assertEqual(t.answer, 'yes')

    def test_codex_matches_turn_id(self):
        t = CodexTurn('n3')
        t.feed({'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': 'mine'}})
        t.feed({'type': 'event_msg', 'payload': {'type': 'user_message', 'message': 'q ⟦bridge n3⟧'}})
        self.assertFalse(t.feed({'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': 'other', 'last_agent_message': 'no'}}))
        self.assertTrue(t.feed({'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': 'mine', 'last_agent_message': 'yes'}}))
        self.assertEqual(t.answer, 'yes')

    def test_claude_interrupt_is_an_error(self):
        t = ClaudeTurn('n2')
        t.feed({'type': 'user', 'message': {'content': [{'type': 'text', 'text': 'q ⟦bridge n2⟧'}]}})
        self.assertTrue(t.feed({'type': 'user', 'message': {'content': '[Request interrupted by user]'}}))
        self.assertIsNone(t.answer)

    def test_write_flags(self):
        self.assertIn('workspace-write', peer_argv('codex', 'tid12345', None, '/w', True, 'p'))
        argv = peer_argv('claude', None, 'sid12345', '/w', True, 'p')
        self.assertIn('acceptEdits', argv)
        self.assertNotIn('--disallowedTools=Edit,Write,NotebookEdit', argv)


if __name__ == '__main__':
    unittest.main()
