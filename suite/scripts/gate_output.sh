#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"
TARGET="${1:?usage: gate_output.sh <mp4|frames_dir>}"
PY="$LAB_MOTOR_ROOT/pipeline/.venv/bin/python"
OUT="$WANGP_LAB_EXPERIMENTS/last_pose_gate_open_end.json"
mkdir -p "$WANGP_LAB_EXPERIMENTS"

if [[ -f "$TARGET" ]]; then
  FRAMES="$WANGP_LAB_ROOT/data/cache/_gate_frames_$$"
  mkdir -p "$FRAMES"
  "$PY" - <<PY
from pathlib import Path
import imageio.v3 as iio
from PIL import Image
vid, out = Path(r"""$TARGET"""), Path(r"""$FRAMES""")
for i, f in enumerate(iio.imread(vid)):
    Image.fromarray(f).save(out / f"{i:04d}.jpg", quality=92)
print("frames", len(list(out.glob("*.jpg"))))
PY
else
  FRAMES="$TARGET"
fi

"$PY" "$LAB_MOTOR_ROOT/pipeline/pose_gate.py" hop \
  --frames "$FRAMES" --mode open_end --json-out "$OUT"
echo "→ $OUT"
"$PY" -c "import json;d=json.load(open(r'$OUT'));print('ok',d.get('ok'),'progress',d.get('progress'),'phase',d.get('phase'));print(d.get('late_open'))"
