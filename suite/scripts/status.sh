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
