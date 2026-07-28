#!/usr/bin/env bash
# Ensure wangp/ exists as a real git clone of upstream Wan2GP.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"
WGP="$WANGP_ROOT"
UPSTREAM="${WANGP_UPSTREAM:-https://github.com/deepbeepmeep/Wan2GP.git}"

if [[ -d "$WGP/.git" ]]; then
  echo "wangp already present: $WGP"
  git -C "$WGP" remote -v | head -2
  git -C "$WGP" log -1 --oneline
  exit 0
fi

if [[ -d "$WGP" ]] && [[ -f "$WGP/wgp.py" ]]; then
  echo "wangp dir exists without .git — leave as-is (local tree)"
  exit 0
fi

echo "Cloning $UPSTREAM → $WGP"
git clone "$UPSTREAM" "$WGP"
echo "Next: create venv + pip install (see wangp/docs/INSTALLATION.md)"
echo "Then: bash $ROOT/suite/scripts/install_bridge.sh"
