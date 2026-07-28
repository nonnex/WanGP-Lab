#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/config/suite.env"
export AIIMGSEQ_LAB_ROOT="$LAB_MOTOR_ROOT"
export AIIMGSEQ_WANGP_ROOT="$WANGP_ROOT"
export WANGP_LAB_CACHE
exec "$WANGP_ROOT/.venv/bin/python" "$ROOT/apps/cli/wan2gp_move_e01.py" "$@"
