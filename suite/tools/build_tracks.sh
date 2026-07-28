#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/configs/suite.env"
LAB="$AIIMGSEQ_LAB_ROOT"
PY="$LAB/pipeline/.venv/bin/python"
FRAMES="${1:-49}"
exec "$PY" "$ROOT/tools/mhr70_to_wanmove_tracks.py" \
  --analysis "$LAB/_data/analysis/0009" \
  --src-still "$LAB/_src/0009_still_day21_10_sophia_dylan_evening_675.jpeg" \
  --still "$LAB/_data/cache/wanmove/still_675_832x480.jpg" \
  --out "$LAB/_data/cache/wanmove/tracks_e01_open_hands_t${FRAMES}.npy" \
  --frames "$FRAMES" --width 832 --height 480 --apart-dx 100 --vis
