#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"
FRAMES="${1:-49}"
APART="${2:-${WANGP_LAB_APART_DX:-100}}"
UF="${3:-${WANGP_LAB_UNCROSS_FRAC:-0.70}}"
PY="$LAB_MOTOR_ROOT/pipeline/.venv/bin/python"
OUT="$WANGP_LAB_CACHE/tracks_e01_open_hands_t${FRAMES}.npy"
ANALYSIS="$WANGP_LAB_CACHE/analysis/0009"
SRC_STILL="$WANGP_LAB_CACHE/src/0009_still_day21_10_sophia_dylan_evening_675.jpeg"
mkdir -p "$WANGP_LAB_CACHE" "$WANGP_ROOT/mask_outputs"

if [[ ! -x "$PY" ]]; then
  echo "motor venv missing: $PY" >&2
  echo "Set LAB_MOTOR_ROOT in config/suite.env (pose_gate / SAM3D host project)." >&2
  exit 2
fi
if [[ ! -d "$ANALYSIS" ]]; then
  echo "missing analysis pack: $ANALYSIS" >&2
  exit 2
fi
if [[ ! -f "$SRC_STILL" ]]; then
  echo "missing src still: $SRC_STILL" >&2
  exit 2
fi

"$PY" "$ROOT/suite/tools/mhr70_to_wanmove_tracks.py" \
  --analysis "$ANALYSIS" \
  --src-still "$SRC_STILL" \
  --still "$WANGP_LAB_CACHE/still_675_832x480.jpg" \
  --out "$OUT" \
  --frames "$FRAMES" --width 832 --height 480 \
  --apart-dx "$APART" --uncross-frac "$UF" --vis

cp -f "$OUT" "$WANGP_ROOT/mask_outputs/$(basename "$OUT")"
if [[ "$APART" != "100" ]]; then
  cp -f "$OUT" "$WANGP_LAB_CACHE/tracks_e01_open_hands_t${FRAMES}_apart${APART}.npy"
fi
echo "→ $OUT  (apart-dx=$APART uncross-frac=$UF)"
