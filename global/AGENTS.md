# Global agent rules (Phát)

Source of truth: `~/Desktop/00.Developer/02.skill/os_ai_agent/global/AGENTS.md`.
Linked as `~/.codex/AGENTS.md` (Codex) and `~/.claude/CLAUDE.md` (Claude Code).
Project-level `AGENTS.md` / `CLAUDE.md` add to or override these rules.

## Communication
- Reply in Vietnamese unless asked otherwise. Keep code, identifiers, commands and commit messages in English.
- Be direct. Say what you verified and what you did not. Never claim something works without running it.

## How to work
- Read the code before changing it. Prefer small, reviewable changes over large rewrites.
- Ground facts in sources: headers, datasheets, official docs, `--help`. Do not invent APIs, register names or CLI flags. Use Context7 for library docs when available, then confirm against the SDK version actually in the project.
- After every code change: build, run the relevant tests / static analysis, and report the result honestly (paste failures).
- For C/C++: respect the project's `compile_commands.json`, toolchain version and coding standard (e.g. MISRA). No undefined behaviour "because it works".
- Record non-obvious decisions in the project's `docs/decisions.md` (what, why, date). Never store secrets there.

## Hardware safety (embedded)
- Never flash, erase, or open a debug session on a real board without asking the user first.
- Never write eFuses / option bytes / lock bits. Tell the user the exact command and let them run it.
- Both agents enforce this: Claude via `~/.claude/settings.json` permissions, Codex via `~/.codex/rules/embedded-safety.rules`. These are guard rails, not a security boundary.

## Working with the other agent
- Claude ⇄ Codex cross-review is encouraged for non-trivial changes: the writer should not be the only reviewer.
- Claude → Codex: `/codex:review`, `/codex:rescue`, or skill `ask-codex-live` (visible in the user's open Codex session).
- Codex → Claude: skill `ask-claude` (`claude -p`, read-only by default).
- At most two round-trips per task, then report back to the user. Show the user both sides of the exchange.

## Secrets
- Never print, commit, or send API keys, tokens, `.env` files, or `~/.codex/config.toml` contents to any external service or another agent.
