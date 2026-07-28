#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"
PROFILE="${WANGP_PROFILE}"
ATTN="${WANGP_ATTENTION}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --attention) ATTN="$2"; shift 2 ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done
cd "$WANGP_ROOT"
# shellcheck source=/dev/null
source .venv/bin/activate
export AIIMGSEQ_LAB_ROOT="$LAB_MOTOR_ROOT"
export AIIMGSEQ_WANGP_ROOT="$WANGP_ROOT"
export WANGP_LAB_ROOT WANGP_LAB_CACHE
echo "WanGP-Lab | profile=$PROFILE attention=$ATTN"
echo "  suite $WANGP_LAB_ROOT"
echo "  wangp $WANGP_ROOT"
echo "  motor $LAB_MOTOR_ROOT"
exec python wgp.py --profile "$PROFILE" --attention "$ATTN"
