#!/usr/bin/env bash
# Health check for the shared agent standard. Read-only.
set -uo pipefail
HUB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEDGER="${XDG_STATE_HOME:-$HOME/.local/state}/os_ai_agent/ledger.txt"
ok=0; bad=0
pass() { printf '  \e[32m✔\e[0m %s\n' "$*"; ok=$((ok+1)); }
fail() { printf '  \e[31m✘\e[0m %s\n' "$*"; bad=$((bad+1)); }
chk_link() { if [[ -L "$2" && "$(readlink -f "$2")" == "$(readlink -f "$1")" ]]; then pass "$2"; else fail "$2 not linked to $1"; fi; }

echo "== Versions"
for pin_name in context7 serena basic-memory; do
  if ! python3 "$HUB/tools/skill_hub/pins.py" "$HUB/pins.json" "$pin_name" >/dev/null; then
    fail "invalid or missing pin: $pin_name"
  fi
done
echo "  claude: $(claude --version 2>/dev/null || echo missing)"
echo "  codex:  $(codex --version 2>/dev/null || echo missing)"
for t in clangd clang-tidy cppcheck bear uv; do command -v "$t" >/dev/null && pass "$t found" || echo "  · $t not installed (optional/user step)"; done

echo "== Global instructions"
chk_link "$HUB/global/AGENTS.md" "$HOME/.codex/AGENTS.md"
chk_link "$HUB/global/AGENTS.md" "$HOME/.claude/CLAUDE.md"

echo "== Skills"
if catalog="$(python3 "$HUB/tools/skill_hub/catalog.py" "$HUB")"; then pass "skills.json valid"; else fail "skills.json invalid"; catalog=""; fi
while IFS=$'\t' read -r n d agents; do
  [[ -n "$n" ]] || continue
  [[ -f "$d/SKILL.md" ]] || fail "$n: SKILL.md missing at $d"
  nested=$(find -L "$d" -mindepth 2 -name SKILL.md 2>/dev/null | head -1)
  [[ -z "$nested" ]] || fail "$n: nested SKILL.md ($nested) would be registered as a second skill"
  [[ ",$agents," == *",claude,"* ]] && chk_link "$d" "$HOME/.claude/skills/$n"
  if [[ ",$agents," == *",codex,"* ]]; then
    chk_link "$d" "$HOME/.agents/skills/$n"
    [[ -e "$HOME/.codex/skills/$n" && ! -L "$HOME/.codex/skills/$n" ]] && fail "duplicate skill in ~/.codex/skills/$n"
  fi
done <<< "$catalog"
if err="$(python3 "$HUB/tools/skill_hub/catalog.py" "$HUB" --check-upstream 2>&1 >/dev/null)"; then
  pass "wrapper skills: upstream links point at the pinned catalog files"
else
  fail "$err (git submodule update --init?)"
fi
# Stale links: point into this hub but the skill is not (or no longer) meant for that agent.
for pair in "claude:$HOME/.claude/skills" "codex:$HOME/.agents/skills"; do
  agent="${pair%%:*}"; root="${pair#*:}"
  for l in "$root"/*; do
    [[ -L "$l" && "$(readlink "$l")" == "$HUB/"* ]] || continue
    awk -F'\t' -v n="$(basename "$l")" -v a="$agent" '$1==n && (","$3",") ~ (","a",") {f=1} END{exit !f}' <<< "$catalog" && continue
    if [[ -f "$LEDGER" ]] && grep -qxF "LINK	$l	$(readlink "$l")" "$LEDGER"; then
      fail "stale link $l (not in skills.json for $agent; run scripts/install.sh to prune)"
    else
      echo "  · $l: your own link into the hub (not managed, left alone)"
    fi
  done
done
while read -r st sha path rest; do
  [[ -n "$path" ]] || continue
  [[ "$st" == "$sha" ]] && sha="$st"   # clean entries start with a space, which read swallows
  pass "$path pinned at ${sha:0:7}"
done < <(git -C "$HUB" submodule status 2>/dev/null | sed 's/^ /= /')
git -C "$HUB" submodule status 2>/dev/null | grep -qE '^[-+U]' && fail "a submodule is not at its pinned commit (git submodule status)"

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
