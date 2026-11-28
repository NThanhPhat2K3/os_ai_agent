---
name: ask-claude
description: Ask Claude (Claude Code CLI) through the session bridge for a second opinion, a review of changes, or a careful check of a technical claim. Each Codex session keeps ONE paired Claude session (resumed later), opened as the real Claude CLI in Terminator (split pane next to a Terminator caller, else a new window). Use when the user says "hỏi Claude", "nhờ Claude review", "ask Claude", or an independent cross-model review would help.
---

# Ask Claude (paired session, visible)

Use the bridge next to this file. It identifies this Codex session from `CODEX_THREAD_ID`:
- First ask from this Codex session → starts a new Claude session and remembers the pair.
- Later asks from the same Codex session, also after it was closed and resumed (CLI or VS Code extension) → **the same Claude session**. A new Codex session gets a new Claude session.
- Claude runs as its **real interactive CLI** inside tmux (socket `agent-bridge`), resumed on the paired session. If this Codex runs in a Terminator terminal, Claude opens as a **split pane next to it**; from VS Code or other terminals, in a **new Terminator window**. The title/status bar shows both session ids. The user can read along and type into it.
- If the Claude CLI is still open, the message is pasted into it; if it was closed, it is reopened on the same session.
- The answer is read from Claude's own transcript. Each message ends with a tag `⟦bridge <nonce>⟧` so turns the user typed by hand are never taken as the reply.

Do not call `claude -p` directly for this skill: it creates unpaired sessions.

## 1. Ask

```bash
~/.agents/skills/ask-claude/bridge ask --to claude -m - <<'EOF'
[Codex → Claude] <self-contained request>
EOF
```
- The bridge starts tmux/Terminator on the desktop, needs network and writes `~/.local/state/os_ai_agent/bridge/`, so it cannot work inside the sandbox. Request to run it outside the sandbox, with a long timeout (Claude can take minutes). If that is denied or unavailable, do not work around it: give the user the exact command to run themselves (`! <command>` style) and stop.
- stdout = Claude's final answer only. stderr has a `[bridge] …` line with both session ids and how Claude was shown.
- Claude does not see this conversation, but it remembers earlier asks in the same pair. Name files, diff ranges and exact questions. Ask Claude to answer in Vietnamese if the user writes in Vietnamese.
- Default mode: Claude's file-edit tools (Edit/Write/NotebookEdit) are disallowed; Read/Grep/Glob and `git diff/status/log/show` are pre-approved; anything else needs the user's approval in the Claude pane. This is not a hard sandbox. `--write` (only when the user explicitly wants Claude to edit) allows edits. Switching mode restarts the idle CLI on the same session.
- `--new` starts a fresh Claude session for this Codex session. Only when the user asks.
- The pair is bound to the working directory of its first ask; Claude always runs there.

## 2. Other commands
- `bridge status`: the Claude session paired with this Codex session and whether its CLI is open (`--all` for every pair).
- `bridge open --to claude`: show the paired Claude CLI again (reopens it on the same session if it was closed).
- `AGENT_BRIDGE_LAYOUT=window` forces a separate window instead of a split pane.

## 3. Errors
- A `[bridge] … has not taken the message yet` line with a screen excerpt: Claude is waiting for the user (e.g. first-time "trust this folder", login, a permission prompt). Tell the user to answer it in that pane/window; never answer trust or login prompts yourself.
- Exit 3: another ask for this pair is running, or the Claude CLI is busy / waiting for the user (the bridge never pastes into a busy CLI or a dialog). Tell the user what the screen excerpt shows; retry once it is idle.
- Exit 4: no answer (CLI exited, turn interrupted, or timeout). Show the stderr to the user; do not invent an answer. If `claude` is not logged in, tell the user to run `claude` once in a terminal.

## Rules
- Do not loop: call Claude at most twice per task, then report back to the user.
- Show Claude's findings faithfully; say which you applied and which you disagree with and why.
- Never copy Claude's transcript into git, memory or other services.
