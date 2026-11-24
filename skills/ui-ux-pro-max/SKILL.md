---
name: ui-ux-pro-max
description: "UI/UX design intelligence for web, mobile, and desktop. This skill should be used when designing, building, reviewing, or fixing interfaces, including pages, components, design systems, accessibility, interaction, responsive layout, typography, color, charts, and stack-specific UI implementation. Searchable local data: 80 searchable styles (51 active), 192 product palettes and reasoning profiles, 74 font pairings, 120 UX guidelines, 105 icons, 17 GSAP presets, 25 chart types, and 22 stacks."
---

# ui-ux-pro-max (wrapper)

Upstream: [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT),
pinned in `vendor/nextlevelbuilder-ui-ux-pro-max-skill`. Its SKILL.md is linked here as `upstream.md`,
and its `scripts/`, `data/` and `references/` folders are linked next to it (no second SKILL.md, so agents
that scan folders recursively do not register the upstream copy as another skill).

1. Read `upstream.md` and follow it. Its relative links (references/, data/) work from this folder.
2. Upstream commands look like `python "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py" ARGS`.
   That variable is not set in this setup. Run instead, with the same ARGS:
   `bash <folder containing this SKILL.md>/search.sh ARGS`
   (example: `bash ~/.claude/skills/ui-ux-pro-max/search.sh "fintech dashboard" --design-system`;
   on Codex the folder is `~/.agents/skills/ui-ux-pro-max`).
3. The search is local (bundled CSV data); it needs only `python3`, no network.
4. The project's own design system, stack and AGENTS.md rules take precedence over suggestions.
