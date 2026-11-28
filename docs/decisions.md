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
