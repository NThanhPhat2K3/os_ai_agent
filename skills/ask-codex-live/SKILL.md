---
name: ask-codex-live
description: Send a message from Claude Code into the user's currently open Codex CLI session (visible in real time) with `codex queue`, then read Codex's reply back. Use when the user says "hỏi Codex", "gửi cho Codex", "bàn với Codex", or wants to watch Claude and Codex talk.
---

# Ask Codex (live session)

The user wants to SEE the conversation. Do not use hidden `codex exec` for this; send into their open session.

## 1. Find the session (do not guess)
- Candidate = newest entry in `~/.codex/session_index.jsonl` (`id`, `thread_name`), but "newest" is not always "open".
- Count interactive Codex processes: `ps -eo pid,tty,args | grep -E '[c]odex( |$)' | grep -v app-server`. If there is more than one, or the candidate's rollout file was not modified recently, ASK the user which session (they can run `/status` in Codex) before sending.
- Rollout log: `ls ~/.codex/sessions/*/*/*/rollout-*-<id>.jsonl`.

## 2. Send
```bash
R=<rollout file>; B=$(wc -l < "$R")
codex queue --thread <id> --message "[Claude → Codex] <self-contained request>"
```
- Codex does not see the Claude conversation: name files, pages, diff ranges, and the exact questions.
- Say whether Codex may edit files or install anything (default: NO, review only).
- Ask for a bounded answer (language, bullet points, word limit).

## 3. Read the reply
Wait in the background (no foreground sleep) until an event whose JSON `payload.type` is `task_complete` (or `turn_aborted`) appears after line `$B`. Parse the JSON; do NOT grep for the string, because Codex may read files that contain it and trigger a false match. Then print only Codex's FINAL answer for that turn (`phase == "final_answer"`), not its progress commentary:
```bash
tail -n +$((B+1)) "$R" | python3 -c '
import sys,json
for l in sys.stdin:
    try: p=json.loads(l).get("payload",{})
    except Exception: continue
    if p.get("type")=="message" and p.get("role")=="assistant" and p.get("phase")=="final_answer":
        for c in p.get("content",[]):
            if c.get("text"): print(c["text"])'
```
If the turn ends with `turn_aborted` or no final answer, tell the user instead of inventing one.

## 4. Report
Show the user: what Claude asked, Codex's answer (verbatim or near-verbatim), then Claude's assessment (agree / disagree / changed plan). At most two round-trips per task.

## Privacy
Rollout logs can contain secrets and tool output. Read only the new assistant messages; never copy logs into memory, git, or other services.
