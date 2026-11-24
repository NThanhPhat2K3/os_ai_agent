# Instructions for AI agents working in this repo

This repo (`os_ai_agent`) is Phát's shared standard for AI coding agents (Claude Code + Codex).
It installs global rules, shared skills, hardware-safety rules and MCP config into the user's
home directory via symlinks. Read `README.md` for the human-facing overview (Vietnamese).
Talk to the user in Vietnamese.

## If the user asks you to set it up on this machine

Follow these steps in order. Stop and ask the user whenever a step says ASK.

1. **Check prerequisites** and report a table of what is present/missing:
   `git --version`, `python3 --version` (≥ 3.10), `claude --version`, `codex --version`,
   `node --version`, `npm --version`, `gh auth status`, `uv --version`.
   Missing `claude` or `codex` is OK (that side is skipped). Do not install system packages
   or use `sudo` yourself: tell the user the exact command instead.
2. **Submodules:** if `vendor/superpowers/skills` is empty, run `git submodule update --init`.
3. **Company policy (ASK):** ask whether this is a work machine with restrictions on sending
   code to external services. If yes or unsure, plan to use `--no-context7` and skip
   `--with-token-tools` unless the user explicitly wants them.
4. **Existing global instructions (ASK):** if `~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md`
   already exist and are not symlinks into this repo, show the user their content. The
   installer will back them up and replace them. Ask whether rules there must be kept; if so,
   propose adding them to `global/AGENTS.md` (as a commit) or to project-level files.
5. **Dry run:** `scripts/install.sh --dry-run [flags]`. Show the user a short summary
   (links to create, conflicts that will be backed up, permissions added, MCP servers).
6. **Install (ASK for go-ahead):** `scripts/install.sh [flags]`.
7. **Verify:** `scripts/doctor.sh` must end with `0 problem(s)`; also `python3 -m unittest`.
   Optional: `scripts/report --no-network --no-open` and report the output path.
8. **Tell the user the manual steps** (README section 4): restart Claude Code and Codex;
   install the Codex plugin in Claude Code (`/plugin marketplace add openai/codex-plugin-cc`,
   `/plugin install codex@openai-codex`, `/codex:setup`); then ask Codex which skills it has.
9. Report honestly: what was done, what was skipped and why, anything that failed (paste output).

Never: run `scripts/install.sh` without the dry run first; edit files under `~/.claude`,
`~/.codex` or `~/.agents` by hand (use the scripts); delete backups in `~/.local/state/os_ai_agent`;
flash or touch hardware; push unrelated or unreviewed changes.

## If you change this repo

- Skills: only through `skills.json` / `scripts/add-skill`. Versions: only in `pins.json` and
  submodule commits. New third-party versions must be ≥ 14 days old.
- Keep `install.sh` idempotent with dry-run, backups and ledger entries that `uninstall.sh` can undo.
- Run `python3 -m unittest` and `scripts/doctor.sh`; test install/uninstall in a fake HOME
  (`HOME=$(mktemp -d) scripts/install.sh`) when touching the scripts.
- Cross-review: ask the other agent to review non-trivial changes (skills `ask-claude` /
  `ask-codex-live`), at most two rounds, and show the user both sides.
- Commit messages in English; end with the co-author line your harness requires.
- **Standing instruction from Phát: after adding, removing or updating a skill (or a pin), once
  doctor and tests pass and the review is done, commit AND push to `origin main` right away**,
  so every machine can `git pull`. The repo is PUBLIC: before pushing, check the diff for secrets,
  API keys, company code or private data, and stop to ask if anything looks sensitive.
