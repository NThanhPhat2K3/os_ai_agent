# Spec: Skill Hub (update checker + dashboard)

Author: Claude (requirements) · Builder: Codex · Reviewer: Claude · Owner: Phát
Status: ready to build · Date: 2026-11-24

## 1. Problem

`os_ai_agent` pins third-party pieces (superpowers skills, MCP servers, CLI plugins).
Upstream releases new versions over time. Phát needs to see what is outdated and update
safely, without silently changing agent behaviour.

## 2. Non-negotiable principles

1. **Check and propose, never auto-apply.** Nothing changes until Phát clicks Apply.
2. **Cooldown:** a release younger than **14 days** is shown as "too new" and is not offered
   as the recommended target (supply-chain caution). Configurable, default 14.
3. **One place for pins.** All pinned versions live in `pins.json` (new). `install.sh`,
   `doctor.sh` and the hub read from it; no version strings duplicated elsewhere.
4. **Every apply is reversible:** done on a git branch, verified by `scripts/doctor.sh`,
   merged only on confirmation, one-click rollback (`git revert`).
5. **Read-only by default:** "Check" only makes HTTP GETs to public registries. It never runs
   downloaded code.

## 3. What to track

| id | kind | source of "latest" | current pin |
|---|---|---|---|
| superpowers | git submodule `vendor/superpowers` | GitHub `obra/superpowers`: latest commit on `main` + tags; `RELEASE-NOTES.md` | submodule commit |
| context7 | npm `@upstash/context7-mcp` | `https://registry.npmjs.org/@upstash/context7-mcp` (`time` map) | `pins.json` |
| serena | PyPI `serena-agent` | `https://pypi.org/pypi/serena-agent/json` | `pins.json` (optional component) |
| basic-memory | PyPI `basic-memory` | `https://pypi.org/pypi/basic-memory/json` | `pins.json` (optional component) |
| codex-plugin-cc | Claude plugin `codex@openai-codex` | GitHub `openai/codex-plugin-cc` releases/tags | installed version from `~/.claude/plugins/cache/openai-codex/codex/<ver>` (info only) |
| claude-cli / codex-cli | CLIs | `claude --version`, `codex --version` vs npm/GitHub latest | info only, no apply |

For **superpowers**, also report which of the *enabled* skills
(`systematic-debugging`, `test-driven-development`, `verification-before-completion`)
changed between the pinned commit and the candidate, and whether any enabled skill gained a new
`REQUIRED SUB-SKILL` / `superpowers:<name>` reference to a skill that is not enabled.
That is a **warning**, because it breaks the "self-contained trio" assumption.

Local skills (`skills/*`) have no upstream: show them as "local", with last git commit date.

## 4. Status model (per item)

`up-to-date` · `update-available` (latest ≥ cooldown) · `too-new` (only releases < cooldown) ·
`warning` (e.g. new dependency on a disabled skill) · `error` (network/parse) · `info-only`.

## 5. User interface

Local web dashboard, **Python 3 standard library only** (no pip/npm install):

- `scripts/skill-hub` starts `http.server` on **127.0.0.1** and a free port, prints the URL, and
  opens it with `xdg-open` if available. Stops on Ctrl+C.
- Single self-contained HTML page (inline CSS/JS, no CDN).
- Look and feel: modern and colourful but readable. Dark theme by default, light toggle.
  A card per item with a coloured status badge, current → latest, release age ("3 days ago"),
  short changelog excerpt, and counts at the top (e.g. 5 up-to-date · 1 update · 1 too new).
  Works at 400 px width.
- Buttons per card: **Check** (refresh), **Preview** (diff of changed files; for skills, a
  SKILL.md diff with added/removed lines coloured), **Apply** (see §6), **Rollback** (shown after
  an apply). A global "Check all" button.
- Every mutating request needs a per-session CSRF token. No secrets ever rendered.

CLI mode for scripts and cron, same engine:
`scripts/skill-hub --check [--json]` prints a table (or JSON) and exits 0 when nothing is
outdated and 10 when updates are available.

## 6. Apply flow

1. Refuse if the working tree is dirty or not on `main`.
2. `git switch -c update/<id>-<version>`.
3. Change the pin: `pins.json`, or for superpowers `git -C vendor/superpowers checkout <sha>` then
   stage the submodule.
4. Run `scripts/doctor.sh` and the rules tests; show the output in the UI.
5. If they pass: commit (`chore(update): <id> <old> -> <new>`) and show **Merge** / **Discard**.
   Merge = fast-forward `main`. Discard = delete the branch, back to `main`.
6. Rollback after merge = `git revert <commit>` on `main` + doctor.
7. Never run `install.sh` automatically. After merge, tell the user the exact command to re-apply
   (`scripts/install.sh`) and that Claude/Codex must be restarted.

## 7. Engineering requirements

- Code in `tools/skill_hub/` (package) + thin launcher `scripts/skill-hub`. Python ≥ 3.10.
- All subprocess calls use argument lists (no `shell=True`); validate ids against the known list.
- Network: 10 s timeout per request, run checks concurrently, degrade gracefully offline.
  Use `gh api` if `gh` is authenticated, otherwise anonymous GitHub API (handle rate limit).
- Cache last results in `~/.cache/os_ai_agent/skill-hub.json` (not in git).
- Refactor `install.sh` and `doctor.sh` to read versions from `pins.json`
  (e.g. via a small `python3 -c` helper); keep existing behaviour and tests passing.
- Tests: `python3 -m unittest` for version comparison, cooldown, status model, superpowers
  dependency warning (fixtures, no network), and the apply flow on a temporary git repo.
- Docs: a README section "Cập nhật skill" in Vietnamese.

## 8. Out of scope (for now)

Auto-scheduling (systemd timer / cron), notifications, updating Claude/Codex CLIs, multi-machine
sync. They can come later behind explicit opt-in.

## 9. Acceptance criteria

- [ ] `scripts/skill-hub --check` works offline (shows `error` per item, no crash) and online.
- [ ] Dashboard renders all items with correct statuses; screenshot-worthy.
- [ ] Apply → doctor → merge → rollback works end-to-end on a throwaway clone of this repo.
- [ ] A release < 14 days old is never the recommended target.
- [ ] `pins.json` is the only place versions are written; `install.sh --dry-run` and
      `doctor.sh` still pass (23/23 on this machine).
- [ ] `python3 -m unittest` passes.
- [ ] No changes outside this repository.
