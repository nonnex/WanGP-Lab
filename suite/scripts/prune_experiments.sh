#!/usr/bin/env bash
# Keep only the latest N experiment runs (+ handoff/leaderboard). Drop the rest.
# Default N=2 (current + previous).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"

KEEP="${WANGP_LAB_KEEP_RUNS:-2}"
DRY=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    ''|*[!0-9]*) ;;
    *) KEEP="$a" ;;
  esac
done

EXP="${WANGP_LAB_EXPERIMENTS:-$ROOT/data/experiments}"
WGP="${WANGP_ROOT:-$ROOT/wangp}"

echo "=== prune experiments (keep=$KEEP dry=$DRY) ==="

# 1) drop incomplete runs first (no result.json / no mp4) — never count toward KEEP
mapfile -t ALL < <(
  find "$EXP" -mindepth 1 -maxdepth 1 -type d -name '*_wan2gp_move_e01' -printf '%T@\t%p\n' 2>/dev/null \
    | sort -nr | cut -f2-
)
RUNS=()
for d in "${ALL[@]}"; do
  ok=0
  [[ -f "$d/result.json" ]] && grep -q '"success": true' "$d/result.json" 2>/dev/null && ok=1
  [[ -n "$(find "$d/outputs" -name '*.mp4' 2>/dev/null | head -1)" ]] && ok=1
  if [[ "$ok" != "1" ]]; then
    sz=$(du -sh "$d" 2>/dev/null | awk '{print $1}')
    if [[ "$DRY" == "1" ]]; then echo "  would rm incomplete $(basename "$d") ($sz)"
    else rm -rf "$d"; echo "  rm incomplete $(basename "$d") ($sz)"; fi
  else
    RUNS+=("$d")
  fi
done
n=${#RUNS[@]}
echo "complete run dirs: $n (keep $KEEP)"
if (( n > KEEP )); then
  for ((i = KEEP; i < n; i++)); do
    d="${RUNS[$i]}"
    sz=$(du -sh "$d" 2>/dev/null | awk '{print $1}')
    if [[ "$DRY" == "1" ]]; then
      echo "  would rm $d ($sz)"
    else
      rm -rf "$d"
      echo "  rm $(basename "$d") ($sz)"
    fi
  done
fi

mapfile -t LOGS < <(ls -1t "$EXP"/l3_*.log "$EXP"/*_console.log 2>/dev/null || true)
if ((${#LOGS[@]} > KEEP)); then
  for ((i = KEEP; i < ${#LOGS[@]}; i++)); do
    f="${LOGS[$i]}"
    [[ -f "$f" ]] || continue
    if [[ "$DRY" == "1" ]]; then echo "  would rm $f"
    else rm -f "$f"; echo "  rm $(basename "$f")"; fi
  done
fi

for d in "$ROOT"/data/cache/_gate_frames_*; do
  [[ -d "$d" ]] || continue
  if [[ "$DRY" == "1" ]]; then echo "  would rm $d"
  else rm -rf "$d"; echo "  rm $(basename "$d")"; fi
done

if [[ -d "$WGP/outputs" ]]; then
  mapfile -t MP4S < <(
    find "$WGP/outputs" -type f \( -name '*.mp4' -o -name '*.webm' \) -printf '%T@\t%p\n' 2>/dev/null \
      | sort -nr | cut -f2-
  )
  if ((${#MP4S[@]} > KEEP)); then
    for ((i = KEEP; i < ${#MP4S[@]}; i++)); do
      f="${MP4S[$i]}"
      if [[ "$DRY" == "1" ]]; then echo "  would rm $f"
      else rm -f "$f"; echo "  rm wangp/outputs/$(basename "$f")"; fi
    done
  fi
fi

# old mask_outputs aliases (mission SoT names kept)
if [[ -d "$WGP/mask_outputs" ]]; then
  shopt -s nullglob
  for f in \
    "$WGP/mask_outputs"/lab_e01_open_t*.npy \
    "$WGP/mask_outputs"/lab_e01_open_t*.vis.jpg \
    "$WGP/mask_outputs"/tracks_e01_open_t*.npy \
    "$WGP/mask_outputs"/lab_still_*.jpg
  do
    if [[ "$DRY" == "1" ]]; then echo "  would rm $f"
    else rm -f "$f"; echo "  rm mask_outputs/$(basename "$f")"; fi
  done
  shopt -u nullglob
fi

find "$ROOT/suite" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true

echo "--- remaining ---"
du -sh "$EXP"/* 2>/dev/null | sort -h || true
echo "OK"
