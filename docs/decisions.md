# Decisions

## 2026-11-28 — Claude ⇄ Codex session bridge
- **What:** `scripts/agent-bridge` (+ `tools/agent_bridge/`) replaces `codex queue` (Claude → Codex) and bare
  `claude -p` (Codex → Claude). It pairs the caller session (`CLAUDE_CODE_SESSION_ID` / `CODEX_THREAD_ID`, set by
  each CLI for its shell tools) with ONE peer session, stored in `~/.local/state/os_ai_agent/bridge/pairs.json`.
- **Why:** every cross-agent call used to start an unrelated session, and the user could not see the exchange.
- **How the peer runs:** the real interactive CLI (`codex resume <id>`, `claude --resume <id>`; new:
  `codex …` / `claude --session-id <uuid>`) inside tmux (socket `agent-bridge`). A Terminator split pane
  (`remotinator vsplit` on the caller's `TERMINATOR_UUID`) when the caller is in Terminator, else a new Terminator
  window. tmux is what lets us paste into a CLI that is already open: Claude has no CLI to message a running
  interactive session.
- **Reading the answer:** from the peer's own transcript (Codex rollout `task_complete.last_agent_message`, Claude
  project jsonl `stop_reason == end_turn`), scoped by a `⟦bridge <nonce>⟧` tag so turns typed by the user are ignored.
  Rejected: headless `exec`/`-p` with a rendered log (first version): reliable, but the user wanted the real CLI.
- **Safety:** no edits by default (`codex -s read-only -a on-request`; Claude with Edit/Write disallowed, other tools
  ask the user in the pane: not a hard sandbox); never paste into a CLI that is busy or has not yet taken the
  previous bridge message (startup dialogs like trust/update, where Enter would pick an option); full session ids in
  tmux names (UUIDv7 ids share prefixes); caller session/terminal variables stripped from the peer;
  `AGENT_BRIDGE_DEPTH` refuses nested calls; one ask per pair (flock); `--new` is persisted before starting; a peer
  id is recorded only once the peer really created it; trust/login prompts are left to the user.
- **Review:** Codex reviewed via the bridge itself, two rounds (2026-11-28); all findings fixed except passing the full caller
  environment explicitly (would expose values in process arguments; the peer is the user's own CLI anyway).
  Known residual risk: if the user is typing in the peer CLI's input box at the moment of a paste, the texts mix
  (a TUI's input box state is not observable); documented in README.

## 2026-11-28 — Bridge: resumable waits instead of one long blocking call
- **What:** `ask --wait N` returns exit 75 (EX_TEMPFAIL) when the peer is still working; `agent-bridge wait --to X`
  resumes waiting for the last ask (`last_nonce` in pairs.json). A killed bridge loses nothing: the answer stays in
  the peer transcript and `wait` reads it.
- **Why:** "timeouts" came from the callers, not the peer: Codex's `exec_command` yields after ~10–30 s and the
  model often gives up instead of polling; Claude's Bash tool cuts foreground commands at 2–10 min. Short slices fit
  both.

## 2026-11-28 — Bridge: fixes from a real Codex → Claude end-to-end test
- **No environment marker for peers.** The CLI Codex runs tool commands in a shared `codex app-server` daemon that
  outlives the CLI that started it. The daemon was first started by a bridge-launched peer, so its
  `AGENT_BRIDGE_DEPTH=1` reached every later Codex session and every Codex → Claude ask was refused as "nested".
  Nested calls are now refused by pair state (the caller session is a recorded peer), and peers get the marker cleared.
- **No split pane for callers inside that daemon:** its `TERMINATOR_UUID` belongs to whoever started the daemon, so
  the bridge opens a new window instead of guessing a pane.
- **Claude turn end:** one assistant message is written as several entries (thinking, text…), each with
  `stop_reason: end_turn`. The turn now ends at the `system` `stop_hook_summary`/`turn_duration` entry (or after 3 s of
  quiet), not at the first `end_turn` (which returned an empty answer).

## 2026-11-28 — Bridge: split pane next to a Codex CLI caller
- **What:** for a caller running inside Codex's shared app-server daemon, find the caller's terminal from the
  interactive `codex` TUI process instead of our own environment: the one started on the thread (`codex resume <id>`),
  else the only one with a `TERMINATOR_UUID` in the same directory; ambiguous → new window. Commands under the VS Code
  extension's or desktop app's app-server always get a new window. `remotinator` is called with that TUI's
  `TERMINATOR_DBUS_*` so it talks to the right Terminator instance.
- **Why:** the user wants one window with both CLIs side by side; Codex → Claude used to always open a new window.
- **Verified:** real Codex CLI in Terminator → Claude opened as a split pane in the same window (2026-11-28).

## 2026-11-28 — Pin updates
- context7 4.6.0 → 4.7.0, ccusage 20.0.48 → 20.0.50, tokscale 4.21.0 → 4.22.1, skills-cli 1.7.6 → 1.8.1,
  trailofbits-skills e4dd0bb → 149d7b2 (only adds an unrelated skill; `modern-cpp` unchanged). All ≥ 14 days old.
- `install.sh` leaves an existing MCP entry untouched, so Codex's context7 stays on the old version until it is
  re-added (see README "Cập nhật").
- Heads-up: Jeffallan/claude-skills is moving skills from `skills/` to `plugin/skills/` (commits still < 14 days).
  The next bump of that vendor must change its `skills_dir`, or `embedded-systems` breaks (doctor will flag it).
