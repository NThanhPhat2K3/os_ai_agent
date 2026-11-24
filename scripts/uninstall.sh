#!/usr/bin/env bash
# Undo exactly what scripts/install.sh recorded in its ledger (newest first).
# Anything that changed since install is left alone and KEPT in the ledger,
# so nothing is silently forgotten. Exit code 1 if something was left.
# Usage: scripts/uninstall.sh [--dry-run]
set -euo pipefail
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/os_ai_agent"
LEDGER="$STATE_DIR/ledger.txt"
DRY=0; [[ "${1:-}" == "--dry-run" ]] && DRY=1
run() { if ((DRY)); then echo "  [dry-run] $*"; else "$@"; fi; }

[[ -f "$LEDGER" ]] || { echo "Nothing to undo (no ledger at $LEDGER)."; exit 0; }
echo "== os_ai_agent uninstall$( ((DRY)) && echo ' [DRY RUN]')"

REMAIN="$(mktemp)"; trap 'rm -f "$REMAIN"' EXIT
mcp_fp() { "$1" mcp get "$2" 2>/dev/null | grep -viE '^[[:space:]]*status:' | sha256sum | cut -d' ' -f1; }
keep() { printf '%s\n' "$1" >> "$REMAIN"; echo "  ~ kept: $2"; }

while IFS= read -r line; do
  IFS=$'\t' read -r kind a b c <<< "$line"
  case "$kind" in
    LINK)   # a=target b=source: remove only if it is still our link
      if [[ -L "$a" && "$(readlink "$a")" == "$b" ]]; then run rm "$a"; echo "  - $a"
      elif [[ ! -e "$a" && ! -L "$a" ]]; then echo "  · $a already gone"
      else keep "$line" "$a changed since install"; fi ;;
    BACKUP) # a=original path b=backup path: restore only into a free slot
      if [[ ! -e "$b" ]]; then keep "$line" "backup $b missing"
      elif [[ -e "$a" || -L "$a" ]]; then keep "$line" "$a is occupied; backup stays at $b"
      else run mkdir -p "$(dirname "$a")"; run mv "$b" "$a"; echo "  ↺ restored $a"; fi ;;
    PERM)   # a=kind b=rule: remove only the rule we added, keep user edits
      if ((DRY)); then echo "  [dry-run] remove permission $a: $b"; else
        python3 - "$HOME/.claude/settings.json" "$a" "$b" <<'PY'
import json, os, sys
p, kind, rule = sys.argv[1:4]
s = json.load(open(p)); perm = s.get("permissions", {}); lst = perm.get(kind, [])
if rule in lst:
    lst.remove(rule)
    if not lst: perm.pop(kind, None)          # don't leave empty lists behind
    if not perm: s.pop("permissions", None)
    mode = os.stat(p).st_mode & 0o777          # keep original permissions
    tmp = p + ".os_ai_agent.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode); os.fchmod(fd, mode)
    with os.fdopen(fd, "w") as f: json.dump(s, f, indent=2, ensure_ascii=False)
    os.replace(tmp, p)
PY
        echo "  - permission $a: $b"; fi ;;
    MCP)    # a=client b=name c=fingerprint: remove only if the full config is unchanged
      if ! "$a" mcp get "$b" >/dev/null 2>&1; then echo "  · $a mcp $b already gone"
      elif [[ -n "$c" && "$(mcp_fp "$a" "$b")" == "$c" ]]; then
        if run "$a" mcp remove "$b" >/dev/null 2>&1; then echo "  - $a mcp: $b"; else keep "$line" "$a mcp remove $b failed"; fi
      else keep "$line" "$a mcp $b was reconfigured by the user"; fi ;;
    NPMDIR) # a=private npm prefix created by install.sh (only ever this exact path)
      # Remove only what npm created; keep the folder if the user put anything else in it.
      if [[ "$a" != "$HOME/.local/share/os_ai_agent/node" ]]; then keep "$line" "unexpected NPMDIR path $a"
      elif [[ ! -d "$a" ]]; then echo "  · $a already gone"
      else
        for f in node_modules package.json package-lock.json; do [[ -e "$a/$f" ]] && run rm -rf -- "$a/$f"; done
        if ((DRY)) || rmdir -- "$a" 2>/dev/null; then echo "  - $a"
        else keep "$line" "$a has extra files, left in place"; fi
      fi ;;
    UVTOOL) # a=package
      if run uv tool uninstall "$a" >/dev/null 2>&1; then echo "  - uv tool: $a"; else keep "$line" "uv tool uninstall $a failed"; fi ;;
    "") ;;
    *) keep "$line" "unknown ledger entry" ;;
  esac
done < <(tac "$LEDGER")

if ((DRY)); then echo "== dry run, nothing changed"; exit 0; fi
mv "$LEDGER" "$LEDGER.undone-$(date +%Y%m%d-%H%M%S)"
if [[ -s "$REMAIN" ]]; then
  tac "$REMAIN" > "$LEDGER"   # back to install order
  echo "== partially done: $(wc -l < "$LEDGER") item(s) left in $LEDGER (fix them, then rerun)"
  exit 1
fi
echo "== done (backups kept under $STATE_DIR/backups)"
