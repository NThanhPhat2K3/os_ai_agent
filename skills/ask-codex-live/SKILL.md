---
name: ask-codex-live
description: Ask Codex from Claude Code through the session bridge. Each Claude session keeps ONE paired Codex session (resumed after restarts), opened as the real Codex CLI in Terminator (split pane next to a Terminator caller, else a new window). Use when the user says "hỏi Codex", "gửi cho Codex", "nhờ Codex review", "bàn với Codex", or a cross-model review would help.
---

# Ask Codex (paired session, visible)

Use the bridge next to this file. It identifies this Claude session from `CLAUDE_CODE_SESSION_ID`:
- First ask from this Claude session → starts a new Codex session and remembers the pair.
- Later asks from the same Claude session, also after it was closed and resumed (e.g. the next morning) → **the same Codex session**. A new Claude session gets a new Codex session.
- Codex runs as its **real interactive CLI** inside tmux (socket `agent-bridge`), resumed on the paired session. If this Claude runs in a Terminator terminal, Codex opens as a **split pane next to it**; otherwise in a **new Terminator window**. The title/status bar shows both session ids. The user can read along and type into it.
- If the Codex CLI is still open, the message is pasted into it; if it was closed, it is reopened on the same session.
- The answer is read from Codex's own rollout. Each message ends with a tag `⟦bridge <nonce>⟧` so turns the user typed by hand are never taken as the reply.

Do not use `codex exec`, `codex queue` or `/codex:rescue` for this skill: they create unpaired sessions.

## 1. Ask

```bash
~/.claude/skills/ask-codex-live/bridge ask --to codex -m - <<'EOF'
[Claude → Codex] <self-contained request>
EOF
```
- Run it with the Bash tool's `run_in_background: true` (Codex can take minutes); you are notified when it ends. Do not poll.
- stdout = Codex's final answer only. stderr has a `[bridge] …` line with both session ids and how Codex was shown.
- Codex does not see this conversation, but it remembers earlier asks in the same pair. Name files, diff ranges and exact questions; ask for a bounded answer (language, bullets, word limit).
- Default mode: Codex sandbox `read-only` with approvals `on-request` (Codex asks the user in its pane before anything outside the sandbox). `--write` (only when the user explicitly wants Codex to edit) uses `workspace-write`. Switching mode restarts the idle CLI on the same session.
- `--new` starts a fresh Codex session for this Claude session. Only when the user asks.
- The pair is bound to the working directory of its first ask; Codex always runs there.

## 2. Other commands
- `bridge status`: the Codex session paired with this Claude session and whether its CLI is open (`--all` for every pair).
- `bridge open --to codex`: show the paired Codex CLI again (reopens it on the same session if it was closed).
- `AGENT_BRIDGE_LAYOUT=window` forces a separate window instead of a split pane.

## 3. Errors
- A `[bridge] … has not taken the message yet` line with a screen excerpt: Codex is waiting for the user (e.g. first-time "Trust this folder?", login). Tell the user to answer it in that pane/window; never answer trust or login prompts yourself.
- Exit 3: another ask for this pair is running, or the Codex CLI is busy / waiting for the user (the bridge never pastes into a busy CLI or a dialog). Tell the user what the screen excerpt shows; retry once it is idle.
- Exit 4: no answer (CLI exited, turn interrupted, or timeout). Show the stderr to the user; do not invent an answer. On timeout the CLI stays open and the answer will appear there.

## 4. Report
Show the user what you asked, Codex's answer (verbatim or near-verbatim), then your assessment (agree / disagree / changed plan). At most two round-trips per task. Never copy Codex's rollout into git, memory or other services.
