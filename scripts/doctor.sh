#!/usr/bin/env bash
# Health check for the shared agent standard. Read-only.
set -uo pipefail
HUB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ok=0; bad=0
pass() { printf '  \e[32m✔\e[0m %s\n' "$*"; ok=$((ok+1)); }
fail() { printf '  \e[31m✘\e[0m %s\n' "$*"; bad=$((bad+1)); }
chk_link() { if [[ -L "$2" && "$(readlink -f "$2")" == "$(readlink -f "$1")" ]]; then pass "$2"; else fail "$2 not linked to $1"; fi; }

echo "== Versions"
echo "  claude: $(claude --version 2>/dev/null || echo missing)"
echo "  codex:  $(codex --version 2>/dev/null || echo missing)"
for t in clangd clang-tidy cppcheck bear uv; do command -v "$t" >/dev/null && pass "$t found" || echo "  · $t not installed (optional/user step)"; done

echo "== Global instructions"
chk_link "$HUB/global/AGENTS.md" "$HOME/.codex/AGENTS.md"
chk_link "$HUB/global/AGENTS.md" "$HOME/.claude/CLAUDE.md"

echo "== Skills"
for d in "$HUB"/skills/*/ "$HUB"/vendor/superpowers/skills/{systematic-debugging,test-driven-development,verification-before-completion}/; do
  n="$(basename "$d")"; chk_link "${d%/}" "$HOME/.claude/skills/$n"; chk_link "${d%/}" "$HOME/.agents/skills/$n"
  [[ -e "$HOME/.codex/skills/$n" && ! -L "$HOME/.codex/skills/$n" ]] && fail "duplicate skill in ~/.codex/skills/$n"
done
sub="$(git -C "$HUB" submodule status vendor/superpowers 2>/dev/null)"
[[ "$sub" == " "* ]] && pass "superpowers pinned at ${sub:1:7}" || fail "superpowers submodule not at pinned commit: $sub"

echo "== Safety"
chk_link "$HUB/safety/codex/embedded-safety.rules" "$HOME/.codex/rules/embedded-safety.rules"
R="$HUB/safety/codex/embedded-safety.rules"
expect() { local want="$1"; shift; got="$(codex execpolicy check --rules "$R" -- "$@" 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("decision","allow-default"))' 2>/dev/null)"; [[ "$got" == "$want" ]] && pass "codex: '$*' → $got" || fail "codex: '$*' → $got (want $want)"; }
expect forbidden espefuse.py burn_efuse X
expect forbidden idf.py efuse-burn
expect forbidden idf.py -p /dev/ttyUSB0 efuse-burn
expect forbidden python3 -m espefuse burn_efuse X
expect prompt idf.py -p /dev/ttyS9 efuse-burn
expect prompt idf.py -p /dev/ttyUSB0 flash
expect prompt openocd -f board.cfg
expect allow-default idf.py build
python3 - "$HUB/safety/claude/permissions.json" "$HOME/.claude/settings.json" <<'PY' && pass "claude: all deny/ask rules present" || fail "claude: permissions missing (run install.sh)"
import json, sys
frag = json.load(open(sys.argv[1])); s = json.load(open(sys.argv[2])).get("permissions", {})
missing = [r for k in ("deny", "ask") for r in frag[k] if r not in s.get(k, [])]
sys.exit(1 if missing else 0)
PY

echo "== MCP"
claude mcp list 2>/dev/null | grep -E "^(context7|serena|basic-memory):" | sed 's/^/  claude: /'
codex mcp list 2>/dev/null | awk 'NR>1 && $1 ~ /^(context7|serena|basic-memory)$/ {print "  codex:  " $1 "  " $NF}'

echo "== Result: $ok ok, $bad problem(s)"
((bad == 0))
