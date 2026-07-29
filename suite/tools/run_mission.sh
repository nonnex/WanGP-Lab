#!/usr/bin/env bash
# Headless run for any suite mission recipe.
#   bash suite/tools/run_mission.sh e01_uncross_open --level L2
#   bash suite/tools/run_mission.sh e01_uncross_open --level L2 --seed 7 --steps 16
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"

MISSION="${1:-}"
if [[ -z "$MISSION" || "$MISSION" == -* ]]; then
  echo "usage: $0 <mission_id> [--level L2] [--seed N] [--steps N] [--frames N]" >&2
  echo "missions:" >&2
  "$WANGP_ROOT/.venv/bin/python" "$ROOT/suite/tools/mission_lib.py" list >&2 || true
  exit 2
fi
shift || true

LEVEL=L2
SEED=""
STEPS=""
FRAMES=""
EXTRA=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --level) LEVEL="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    --steps) STEPS="$2"; shift 2 ;;
    --frames) FRAMES="$2"; shift 2 ;;
    *) EXTRA+=("$1"); shift ;;
  esac
done

export WANGP_LAB_MISSION="$MISSION"
# Resolve recipe → still/tracks/prompt via python, then call move runner
ARGS=$(
"$WANGP_ROOT/.venv/bin/python" - <<PY
import json, os, sys
sys.path.insert(0, r"$ROOT/suite/tools")
import mission_lib as M
m = M.load_mission("$MISSION")
step = M.ladder_step(m, "$LEVEL")
frames = int("${FRAMES}" or step.get("frames") or 49)
steps = int("${STEPS}" or step.get("steps") or 16)
seed = int("${SEED}" or step.get("seed") or 33)
still = M.mission_still(m, smoke=("$LEVEL"=="L0"))
tracks = M.mission_tracks(m, frames)
print(json.dumps({
  "still": str(still),
  "tracks": str(tracks),
  "frames": frames,
  "steps": steps,
  "seed": seed,
  "prompt": m.get("prompt") or "",
  "negative": m.get("negative_prompt") or "",
  "use_tracks": bool(step.get("use_tracks", True)),
  "mission": m.get("id"),
}))
PY
)

STILL=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['still'])" "$ARGS")
TRACKS=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['tracks'])" "$ARGS")
FR=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['frames'])" "$ARGS")
ST=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['steps'])" "$ARGS")
SD=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['seed'])" "$ARGS")
PR=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['prompt'])" "$ARGS")
NG=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['negative'])" "$ARGS")

echo "mission=$MISSION level=$LEVEL frames=$FR steps=$ST seed=$SD"
echo "still=$STILL"
echo "tracks=$TRACKS"

exec "$WANGP_ROOT/.venv/bin/python" "$ROOT/suite/tools/wan2gp_move_e01.py" \
  --still "$STILL" \
  --tracks "$TRACKS" \
  --frames "$FR" \
  --steps "$ST" \
  --seed "$SD" \
  --prompt "$PR" \
  --negative "$NG" \
  --profile "${WANGP_PROFILE:-4}" \
  --attention "${WANGP_ATTENTION:-sage}" \
  "${EXTRA[@]}"
