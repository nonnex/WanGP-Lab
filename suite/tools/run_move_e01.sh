#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"
export WANGP_LAB_ROOT WANGP_ROOT LAB_MOTOR_ROOT AIIMGSEQ_LAB_ROOT AIIMGSEQ_WANGP_ROOT WANGP_LAB_CACHE WANGP_LAB_EXPERIMENTS
exec "$WANGP_ROOT/.venv/bin/python" "$ROOT/suite/tools/wan2gp_move_e01.py" "$@"
