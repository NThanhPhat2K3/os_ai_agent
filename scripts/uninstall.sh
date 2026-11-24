#!/usr/bin/env bash
# Undo exactly what scripts/install.sh recorded in its ledger (newest first).
# Usage: scripts/uninstall.sh [--dry-run]
set -euo pipefail
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/os_ai_agent"
LEDGER="$STATE_DIR/ledger.txt"
DRY=0; [[ "${1:-}" == "--dry-run" ]] && DRY=1
run() { if ((DRY)); then echo "  [dry-run] $*"; else "$@"; fi; }

[[ -f "$LEDGER" ]] || { echo "Nothing to undo (no ledger at $LEDGER)."; exit 0; }
echo "== os_ai_agent uninstall$( ((DRY)) && echo ' [DRY RUN]')"

tac "$LEDGER" | while IFS=$'\t' read -r kind a b c; do
  case "$kind" in
    LINK)   # a=target b=source: remove only if it is still our link
      if [[ -L "$a" && "$(readlink "$a")" == "$b" ]]; then run rm "$a"; echo "  - $a"; else echo "  ~ $a changed since install, left alone"; fi ;;
    BACKUP) # a=original path b=backup path: restore if the slot is free
      if [[ -e "$b" && ! -e "$a" && ! -L "$a" ]]; then run mkdir -p "$(dirname "$a")"; run mv "$b" "$a"; echo "  ↺ restored $a"; fi ;;
    PERM)   # a=kind b=rule
      if ((DRY)); then echo "  [dry-run] remove permission $a: $b"; else
        python3 - "$HOME/.claude/settings.json" "$a" "$b" <<'PY'
import json, sys
p, kind, rule = sys.argv[1:4]
s = json.load(open(p)); perm = s.get("permissions", {}); lst = perm.get(kind, [])
if rule in lst:
    lst.remove(rule)
    if not lst: perm.pop(kind, None)          # don't leave empty lists behind
    if not perm: s.pop("permissions", None)
    json.dump(s, open(p, "w"), indent=2, ensure_ascii=False)
PY
        echo "  - permission $a: $b"; fi ;;
    MCP)    # a=client b=name
      run "$a" mcp remove "$b" >/dev/null 2>&1 || true; echo "  - $a mcp: $b" ;;
    UVTOOL) # a=package
      run uv tool uninstall "$a" >/dev/null 2>&1 || true; echo "  - uv tool: $a" ;;
  esac
done
((DRY)) || mv "$LEDGER" "$LEDGER.undone-$(date +%Y%m%d-%H%M%S)"
echo "== done (backups kept under $STATE_DIR/backups)"
