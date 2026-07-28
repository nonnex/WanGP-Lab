#!/usr/bin/env bash
# Headless Wan-Move e01 (no Web UI). Prefer stopping UI first to free VRAM:
#   pkill -f 'wgp.py --profile'   # only if no other gen needed
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WGP_PY="/home/nick/AI/_COMMON/VENDORS/Wan2GP/.venv/bin/python"
cd "$ROOT"
exec "$WGP_PY" "$ROOT/lab/tools/wan2gp_move_e01.py" "$@"
