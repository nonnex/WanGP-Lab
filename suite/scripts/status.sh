#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"
echo "=== WanGP-Lab status ==="
echo "suite : $WANGP_LAB_ROOT"
echo "wangp : $WANGP_ROOT  $([ -f "$WANGP_ROOT/wgp.py" ] && echo OK || echo MISSING)"
echo "motor : $LAB_MOTOR_ROOT  $([ -d "$LAB_MOTOR_ROOT" ] && echo OK || echo MISSING)"
echo "wangp venv: $([ -x "$WANGP_ROOT/.venv/bin/python" ] && echo OK || echo MISSING)"
echo "motor venv: $([ -x "$LAB_MOTOR_ROOT/pipeline/.venv/bin/python" ] && echo OK || echo MISSING)"
echo "finetunes in wangp:"
ls "$WANGP_ROOT/finetunes"/lab_*.json 2>/dev/null || echo "  (run install_bridge.sh)"
echo "plugin:"
ls -d "$WANGP_ROOT/plugins/wan2gp-lab-bridge" 2>/dev/null || echo "  (run install_bridge.sh)"
if [[ -f "$WANGP_ROOT/wgp_config.json" ]]; then
  python3 -c "import json;d=json.load(open('$WANGP_ROOT/wgp_config.json'));print('plugins',d.get('enabled_plugins'));print('profile',d.get('profile'),d.get('attention_mode'))"
fi
echo "suite cache:"; ls "$WANGP_LAB_CACHE" 2>/dev/null | head -15
if [[ -f "$ROOT/suite/scripts/with_ort_wsl_env.sh" ]]; then
  echo "ort-drm:"
  bash "$ROOT/suite/scripts/with_ort_wsl_env.sh" --diagnose 2>&1 | sed 's/^/  /'
fi

echo "hygiene:"
if bash "$ROOT/suite/scripts/lab_hygiene.sh" --check --quiet 2>/dev/null; then
  echo "  CLEAN (keep=$WANGP_LAB_KEEP_RUNS)"
else
  echo "  DIRTY — bash suite/scripts/lab_hygiene.sh"
  bash "$ROOT/suite/scripts/lab_hygiene.sh" --check 2>&1 | sed 's/^/  /' | tail -20 || true
fi
echo "outputs: $WANGP_LAB_OUTPUTS  link=$(readlink "$WANGP_ROOT/outputs" 2>/dev/null || echo none)"
if [[ -f "$WANGP_LAB_EXPERIMENTS/LEADERBOARD.tsv" ]]; then
  echo "leaderboard (last 5):"
  tail -5 "$WANGP_LAB_EXPERIMENTS/LEADERBOARD.tsv" | sed 's/^/  /'
fi

