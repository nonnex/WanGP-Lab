#!/usr/bin/env bash
# Stack channel helper: base (rock-solid) vs edge (frontier).
# See suite/docs/STACK_CHANNELS.md
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WANGP="${WANGP_ROOT:-$ROOT/wangp}"
BASE_LINK="$WANGP/.venv"
BASE_SNAP="$WANGP/.venv-base"
EDGE="$WANGP/.venv-edge"

usage() {
  cat <<EOF
Usage: bash suite/scripts/stack_channel.sh <cmd>

  status              show active channel + fingerprints
  use base            point wangp/.venv at base snapshot (if split)
  use edge            point wangp/.venv at .venv-edge
  init-edge-from-base copy current .venv → .venv-edge (once)
  fingerprint         print py/torch/cuda for active .venv

Active runtime path is always: wangp/.venv
Channels are directory names; we rename/swap, we do not upgrade in place.
EOF
}

fp() {
  local py="$1/bin/python"
  if [[ ! -x "$py" ]]; then
    echo "  (missing $1)"
    return
  fi
  "$py" - <<'PY' 2>/dev/null || echo "  (import failed)"
import sys
try:
    import torch
    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    print(f"  py {sys.version.split()[0]}  torch {torch.__version__}  cuda {torch.version.cuda}  gpu {gpu}")
except Exception as e:
    print(f"  py {sys.version.split()[0]}  torch FAIL {e}")
PY
}

cmd="${1:-status}"
case "$cmd" in
  -h|--help) usage; exit 0 ;;
  status)
    echo "wangp: $WANGP"
    echo "active .venv:"
    if [[ -L "$BASE_LINK" ]]; then
      echo "  symlink → $(readlink -f "$BASE_LINK")"
    elif [[ -d "$BASE_LINK" ]]; then
      echo "  directory (not a symlink)"
    else
      echo "  MISSING"
    fi
    echo "fingerprint active:"
    fp "$BASE_LINK"
    echo "snapshots:"
    for d in "$BASE_SNAP" "$EDGE" "$WANGP"/.venv-py*; do
      [[ -e "$d" ]] || continue
      echo "- $(basename "$d")"
      fp "$d"
    done
    echo "docs: suite/docs/STACK_CHANNELS.md suite/docs/WANGP_STACK.md"
    ;;
  fingerprint)
    fp "$BASE_LINK"
    ;;
  init-edge-from-base)
    if [[ -d "$EDGE" ]]; then
      echo "exists: $EDGE (refusing overwrite)" >&2
      exit 1
    fi
    if [[ ! -d "$BASE_LINK" ]]; then
      echo "no active .venv" >&2
      exit 1
    fi
    echo "copying $BASE_LINK → $EDGE (large)…"
    cp -a "$BASE_LINK" "$EDGE"
    echo "OK edge ready. Mutate only $EDGE, then: stack_channel.sh use edge"
    ;;
  use)
    target="${2:-}"
    case "$target" in
      base)
        # Prefer explicit base snap; else keep current .venv as base
        if [[ -d "$EDGE" && -d "$BASE_LINK" && ! -d "$BASE_SNAP" ]]; then
          # if currently on edge content unknown — require base snap
          :
        fi
        if [[ -d "$BASE_SNAP" ]]; then
          if [[ -d "$BASE_LINK" && ! -L "$BASE_LINK" ]]; then
            # park current as edge-park if looks like edge session
            ts=$(date +%Y%m%d_%H%M%S)
            mv "$BASE_LINK" "$WANGP/.venv-parked-$ts"
            echo "parked previous .venv → .venv-parked-$ts"
          elif [[ -L "$BASE_LINK" ]]; then
            rm -f "$BASE_LINK"
          fi
          mv "$BASE_SNAP" "$BASE_LINK"
          echo "active → base (was .venv-base)"
        else
          echo "no .venv-base snapshot. Current .venv IS base. Create edge with init-edge-from-base."
          fp "$BASE_LINK"
        fi
        ;;
      edge)
        if [[ ! -d "$EDGE" ]]; then
          echo "missing $EDGE — run: stack_channel.sh init-edge-from-base" >&2
          exit 1
        fi
        if [[ -d "$BASE_LINK" && ! -d "$BASE_SNAP" ]]; then
          mv "$BASE_LINK" "$BASE_SNAP"
          echo "saved base → .venv-base"
        elif [[ -L "$BASE_LINK" ]]; then
          rm -f "$BASE_LINK"
        elif [[ -d "$BASE_LINK" ]]; then
          ts=$(date +%Y%m%d_%H%M%S)
          mv "$BASE_LINK" "$WANGP/.venv-parked-$ts"
          echo "parked → .venv-parked-$ts"
        fi
        mv "$EDGE" "$BASE_LINK"
        echo "active → edge (was .venv-edge). Rename back with: use base after restoring snaps."
        echo "TIP: after edge session: mv .venv .venv-edge && mv .venv-base .venv"
        ;;
      *)
        echo "use base|edge" >&2
        exit 2
        ;;
    esac
    fp "$BASE_LINK"
    ;;
  *)
    usage
    exit 2
    ;;
esac
