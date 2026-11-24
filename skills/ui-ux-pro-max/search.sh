#!/usr/bin/env bash
# Launcher for the pinned upstream search.py, independent of CLAUDE_PLUGIN_ROOT.
set -euo pipefail
here="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
exec python3 "$here/upstream/scripts/search.py" "$@"
