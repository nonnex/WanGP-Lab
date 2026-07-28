#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"
FRAMES="${1:-49}"
PY="$LAB_MOTOR_ROOT/pipeline/.venv/bin/python"
OUT="$WANGP_LAB_CACHE/tracks_e01_open_hands_t${FRAMES}.npy"
mkdir -p "$WANGP_LAB_CACHE"

"$PY" "$ROOT/suite/tools/mhr70_to_wanmove_tracks.py" \
  --analysis "$LAB_MOTOR_ROOT/_data/analysis/0009" \
  --src-still "$LAB_MOTOR_ROOT/_src/0009_still_day21_10_sophia_dylan_evening_675.jpeg" \
  --still "$WANGP_LAB_CACHE/still_675_832x480.jpg" \
  --out "$OUT" \
  --frames "$FRAMES" --width 832 --height 480 --apart-dx 100 --vis

cp -f "$OUT" "$WANGP_ROOT/mask_outputs/$(basename "$OUT")"
echo "→ $OUT"
