---
name: ask-claude
description: Ask Claude (Claude Code CLI) for a second opinion, a review of changes, or a careful check of a translation/technical claim. Use when the user says "hỏi Claude", "nhờ Claude review", "ask Claude", or when an independent cross-model review would help before finishing a task.
---

# Ask Claude

Claude Code is installed locally as `claude`. Call it non-interactively with `claude -p`.

## Read-only review (default — use this unless the user explicitly asks Claude to edit)

Run from the project root:

```bash
claude -p "<clear, self-contained request>" \
  --permission-mode plan \
  --allowedTools "Read,Grep,Glob,Bash(git diff:*),Bash(git status:*),Bash(git log:*)" \
  --output-format text
```

- Make the prompt self-contained: Claude does not see this Codex conversation. Name the files, PDF pages, or `git diff` range to look at, and say what kind of feedback you want.
- Ask Claude to answer in Vietnamese if the user is writing in Vietnamese.
- Example: `claude -p "Review git diff HEAD~1 for website/docs/chuong-18-phan-1.md. Compare against the book PDF pages 975-981 (use pdftotext). Is it a full translation, not a summary? List concrete issues in Vietnamese." --permission-mode plan --allowedTools "Read,Grep,Glob,Bash(git diff:*),Bash(pdftotext:*)"`

## Rules

- Do not give Claude write permissions unless the user explicitly asks for Claude to make the change.
- Do not loop: call Claude at most twice per task, then report back to the user.
- Show Claude's findings to the user faithfully; say which ones you applied and which you disagree with and why.
- If `claude` is not found or not logged in, tell the user to run `claude` once in a terminal to log in.
