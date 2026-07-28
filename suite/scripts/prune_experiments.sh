#!/usr/bin/env bash
# Workspace retention: keep last N complete Move runs + tiny history.
# Default N=2 (current + previous). Incomplete runs always dropped.
#
#   bash suite/scripts/prune_experiments.sh
#   bash suite/scripts/prune_experiments.sh 3
#   bash suite/scripts/prune_experiments.sh --dry-run
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

rm_() {
  local path="$1"
  local label="${2:-$path}"
  [[ -e "$path" ]] || return 0
  local sz
  sz=$(du -sh "$path" 2>/dev/null | awk '{print $1}')
  if [[ "$DRY" == "1" ]]; then
    echo "  would rm $label ($sz)"
  else
    rm -rf "$path"
    echo "  rm $label ($sz)"
  fi
}

echo "=== prune workspace (keep=$KEEP dry=$DRY) ==="

# --- incomplete experiment dirs first ---
mapfile -t ALL < <(
  find "$EXP" -mindepth 1 -maxdepth 1 -type d -name '*_wan2gp_move_e01' -printf '%T@\t%p\n' 2>/dev/null \
    | sort -nr | cut -f2-
)
RUNS=()
for d in "${ALL[@]}"; do
  ok=0
  if [[ -f "$d/result.json" ]] && grep -q '"success": true' "$d/result.json" 2>/dev/null; then
    ok=1
  fi
  if [[ -d "$d/outputs" ]] && find "$d/outputs" -name '*.mp4' -print -quit 2>/dev/null | grep -q .; then
    ok=1
  fi
  if [[ "$ok" != "1" ]]; then
    rm_ "$d" "incomplete $(basename "$d")"
  else
    RUNS+=("$d")
  fi
done

n=${#RUNS[@]}
echo "complete runs: $n (keep $KEEP)"
if (( n > KEEP )); then
  for ((i = KEEP; i < n; i++)); do
    rm_ "${RUNS[$i]}" "$(basename "${RUNS[$i]}")"
  done
fi

# --- console logs: keep newest KEEP ---
mapfile -t LOGS < <(ls -1t "$EXP"/l3_*.log "$EXP"/*_console.log 2>/dev/null || true)
if ((${#LOGS[@]} > KEEP)); then
  for ((i = KEEP; i < ${#LOGS[@]}; i++)); do
    rm_ "${LOGS[$i]}" "$(basename "${LOGS[$i]}")"
  done
fi

# --- transient gate frame dirs ---
for d in "$ROOT"/data/cache/_gate_frames_*; do
  [[ -e "$d" ]] || continue
  rm_ "$d" "cache/$(basename "$d")"
done

# --- UI outputs (suite _outputs, via wangp/outputs symlink): keep newest KEEP ---
OUT_DIR="${WANGP_LAB_OUTPUTS:-$ROOT/_outputs}"
[[ -d "$OUT_DIR" ]] || OUT_DIR="$WGP/outputs"
if [[ -d "$OUT_DIR" ]]; then
  mapfile -t MP4S < <(
    find "$OUT_DIR" -maxdepth 1 -type f \( -name '*.mp4' -o -name '*.webm' -o -name '*.mov' \) \
      -printf '%T@\t%p\n' 2>/dev/null | sort -nr | cut -f2-
  )
  if ((${#MP4S[@]} > KEEP)); then
    for ((i = KEEP; i < ${#MP4S[@]}; i++)); do
      rm_ "${MP4S[$i]}" "_outputs/$(basename "${MP4S[$i]}")"
    done
  fi
fi

# --- mask_outputs: only mission SoT names ---
if [[ -d "$WGP/mask_outputs" ]]; then
  shopt -s nullglob
  for f in \
    "$WGP/mask_outputs"/lab_e01_open_t*.npy \
    "$WGP/mask_outputs"/lab_e01_open_t*.vis.jpg \
    "$WGP/mask_outputs"/tracks_e01_open_t*.npy \
    "$WGP/mask_outputs"/lab_still_*.jpg
  do
    rm_ "$f" "mask_outputs/$(basename "$f")"
  done
  shopt -u nullglob
fi

# --- suite / plugin bytecode ---
while IFS= read -r -d '' d; do
  rm_ "$d" "${d#"$ROOT"/}"
done < <(find "$ROOT/suite" -type d -name __pycache__ -print0 2>/dev/null)

# --- Kilo IDE junk (never commit; 60MB+) ---
rm_ "$ROOT/.kilo/node_modules" ".kilo/node_modules"
rm_ "$ROOT/.kilo/package.json" ".kilo/package.json"
rm_ "$ROOT/.kilo/package-lock.json" ".kilo/package-lock.json"
rm_ "$ROOT/.kilo/agents/data.md" ".kilo/agents/data.md"

# --- empty logs dir noise ---
find "$ROOT/_logs" -type f ! -name '.gitkeep' -delete 2>/dev/null || true

# --- within kept runs: drop huge api log tails? keep full log (small). OK ---

echo "--- remaining ---"
du -sh "$EXP"/* 2>/dev/null | sort -h || true
du -sh "$ROOT/.kilo" "$OUT_DIR" "$WGP/mask_outputs" "$ROOT/data" 2>/dev/null || true
echo "OK keep=$KEEP"
