#!/usr/bin/env bash
# os_ai_agent installer: link the shared standard into Claude Code and Codex.
# Idempotent. Backs up anything it replaces. Records every action so
# scripts/uninstall.sh can undo exactly what this script did.
#
# Usage: scripts/install.sh [--dry-run] [--with-serena] [--with-basic-memory]
set -euo pipefail

HUB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/os_ai_agent"
LEDGER="$STATE_DIR/ledger.txt"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$STATE_DIR/backups/$STAMP"

DRY=0; WITH_SERENA=0; WITH_BM=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --with-serena) WITH_SERENA=1 ;;
    --with-basic-memory) WITH_BM=1 ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "Unknown option: $a" >&2; exit 2 ;;
  esac
done

# Superpowers skills enabled selectively (self-contained trio; see README).
SUPERPOWERS_SKILLS=(systematic-debugging test-driven-development verification-before-completion)

say()  { printf '%s\n' "$*"; }
run()  { if ((DRY)); then say "  [dry-run] $*"; else "$@"; fi; }
note() { ((DRY)) || { mkdir -p "$STATE_DIR"; printf '%s\n' "$*" >> "$LEDGER"; }; }

backup() { # move an existing path out of the way, remember where it went
  local target="$1" dest="$BACKUP_DIR${1}"
  say "  ! conflict: $target exists -> backup to $dest"
  run mkdir -p "$(dirname "$dest")"
  run mv "$target" "$dest"
  note "BACKUP	$target	$dest"
}

link() { # link <source> <target>
  local src="$1" dst="$2"
  if [[ -L "$dst" && "$(readlink -f "$dst")" == "$(readlink -f "$src")" ]]; then
    say "  = $dst (already linked)"; return
  fi
  if [[ -e "$dst" || -L "$dst" ]]; then backup "$dst"; fi
  run mkdir -p "$(dirname "$dst")"
  run ln -s "$src" "$dst"
  note "LINK	$dst	$src"
  say "  + $dst -> $src"
}

say "== os_ai_agent install (hub: $HUB)$( ((DRY)) && echo ' [DRY RUN]')"

say "-- 1. Global instructions"
link "$HUB/global/AGENTS.md" "$HOME/.codex/AGENTS.md"
link "$HUB/global/AGENTS.md" "$HOME/.claude/CLAUDE.md"

say "-- 2. Skills (whole directories; Claude: ~/.claude/skills, Codex: ~/.agents/skills)"
skill_sources=()
for d in "$HUB"/skills/*/; do skill_sources+=("${d%/}"); done
if [[ -d "$HUB/vendor/superpowers/skills" ]]; then
  for s in "${SUPERPOWERS_SKILLS[@]}"; do skill_sources+=("$HUB/vendor/superpowers/skills/$s"); done
else
  say "  ! vendor/superpowers missing: run 'git submodule update --init' first"
fi
for src in "${skill_sources[@]}"; do
  name="$(basename "$src")"
  link "$src" "$HOME/.claude/skills/$name"
  link "$src" "$HOME/.agents/skills/$name"
  # Avoid duplicate names in Codex's legacy skills root.
  legacy="$HOME/.codex/skills/$name"
  if [[ -e "$legacy" && ! -L "$legacy" ]]; then backup "$legacy"; fi
done

say "-- 3. Safety rules"
link "$HUB/safety/codex/embedded-safety.rules" "$HOME/.codex/rules/embedded-safety.rules"
if ((DRY)); then
  say "  [dry-run] merge $HUB/safety/claude/permissions.json into ~/.claude/settings.json"
else
  python3 - "$HUB/safety/claude/permissions.json" "$HOME/.claude/settings.json" "$BACKUP_DIR" "$LEDGER" <<'PY'
import json, os, shutil, sys
frag_p, settings_p, backup_dir, ledger = sys.argv[1:5]
frag = json.load(open(frag_p))
s = json.load(open(settings_p)) if os.path.exists(settings_p) else {}
perm = s.setdefault("permissions", {})
added = []
for kind in ("deny", "ask"):
    cur = perm.setdefault(kind, [])
    for rule in frag.get(kind, []):
        if rule not in cur:
            cur.append(rule); added.append((kind, rule))
if added:
    if os.path.exists(settings_p):
        dst = os.path.join(backup_dir, settings_p.lstrip("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(settings_p, dst)
        print(f"  backup {settings_p} -> {dst}")
    # Atomic write that keeps the original file mode (umask-proof; default 600).
    mode = os.stat(settings_p).st_mode & 0o777 if os.path.exists(settings_p) else 0o600
    tmp = settings_p + ".os_ai_agent.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    os.fchmod(fd, mode)
    with os.fdopen(fd, "w") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    os.replace(tmp, settings_p)
    with open(ledger, "a") as f:
        for kind, rule in added:
            f.write(f"PERM\t{kind}\t{rule}\n")
print(f"  permissions: {len(added)} rule(s) added, others already present")
PY
fi

pin() { python3 "$HUB/tools/skill_hub/pins.py" "$HUB/pins.json" "$1"; }
CONTEXT7_VERSION="$(pin context7)"
SERENA_VERSION="$(pin serena)"
BASIC_MEMORY_VERSION="$(pin basic-memory)"
say "-- 4. MCP servers"
# Fingerprint of a server's full config (`mcp get` minus the volatile Status line).
# uninstall removes a server only if its fingerprint is unchanged.
mcp_fp() { "$1" mcp get "$2" 2>/dev/null | grep -viE '^[[:space:]]*status:' | sha256sum | cut -d' ' -f1; }
mcp_add() { # mcp_add <client> <name> <command...>
  local client="$1" name="$2"; shift 2
  if "$client" mcp get "$name" >/dev/null 2>&1; then
    say "  = $client: $name (already configured, left untouched)"; return
  fi
  run "$@"
  ((DRY)) || note "MCP	$client	$name	$(mcp_fp "$client" "$name")"
  say "  + $client: $name"
}
mcp_add claude context7 claude mcp add --scope user --transport http context7 https://mcp.context7.com/mcp
mcp_add codex  context7 codex mcp add context7 -- npx -y @upstash/context7-mcp@${CONTEXT7_VERSION}

need_uv() {
  command -v uv >/dev/null || { say "  ! 'uv' not found. Install it first: https://docs.astral.sh/uv/getting-started/installation/"; return 1; }
}
uv_install() { # only record tools this script actually installed
  local pkg="$1" spec="$2"
  if uv tool list 2>/dev/null | grep -q "^$pkg "; then say "  = uv tool $pkg (already installed, left untouched)"; return; fi
  run uv tool install "$spec"
  note "UVTOOL	$pkg"
}
if ((WITH_SERENA)) && need_uv; then
  uv_install serena-agent "serena-agent==${SERENA_VERSION}"
  mcp_add claude serena claude mcp add --scope user serena -- serena start-mcp-server --context claude-code --project-from-cwd
  mcp_add codex  serena codex mcp add serena -- serena start-mcp-server --project-from-cwd --context=codex
fi
if ((WITH_BM)) && need_uv; then
  uv_install basic-memory "basic-memory==${BASIC_MEMORY_VERSION}"
  run mkdir -p "$HOME/agent-memory"; run chmod 700 "$HOME/agent-memory"
  mcp_add claude basic-memory claude mcp add --scope user basic-memory -e BASIC_MEMORY_HOME="$HOME/agent-memory" -- basic-memory mcp
  mcp_add codex  basic-memory codex mcp add basic-memory --env BASIC_MEMORY_HOME="$HOME/agent-memory" -- basic-memory mcp
fi

say "== done. Restart Claude Code and Codex, then run scripts/doctor.sh"
((DRY)) || say "   ledger: $LEDGER"
