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
