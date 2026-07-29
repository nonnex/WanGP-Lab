#!/usr/bin/env bash
# Run a command with WSL ORT DRM discovery handled cleanly (no log filter).
#
# Usage:
#   bash suite/scripts/with_ort_wsl_env.sh --diagnose
#   bash suite/scripts/with_ort_wsl_env.sh wangp/.venv/bin/python -c 'import onnxruntime'
#   bash suite/scripts/with_ort_wsl_env.sh -- "$PY" wgp.py --profile 4
#
# See suite/scripts/lib/ort_wsl_drm.sh and suite/docs/ORT_WSL_DRM.md
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/suite/scripts/lib/ort_wsl_drm.sh"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  sed -n '2,12p' "$0" | sed 's/^# \?//'
  exit 0
fi

if [[ "${1:-}" == "--diagnose" ]]; then
  ort_drm_diagnose
  exit 0
fi

if [[ "${1:-}" == "--" ]]; then
  shift
fi

if [[ $# -lt 1 ]]; then
  echo "usage: with_ort_wsl_env.sh [--diagnose] [--] <cmd> [args...]" >&2
  exit 2
fi

# One-line operator notice (not a suppress filter — explains action)
if ort_drm_is_broken_vgem && [[ "${WANGP_ORT_DRM_NS:-}" != "1" ]]; then
  if ort_drm_unshare_available; then
    echo "ort-drm: WSL vgem card0 has no vendor sysfs → mount-ns empty /sys/class/drm (ORT PCI/EP path)" >&2
    ort_drm_exec_with_clean_sysfs "$@"
    # exec never returns on success
  else
    echo "ort-drm: BROKEN_VGEM but unshare unavailable — ORT will WARN; CUDA EP usually still OK" >&2
    echo "  diagnose: bash suite/scripts/with_ort_wsl_env.sh --diagnose" >&2
    export WANGP_ORT_DRM_STATUS=broken_vgem_no_ns
  fi
else
  if [[ "${WANGP_ORT_DRM_NS:-}" == "1" ]]; then
    export WANGP_ORT_DRM_STATUS=ns_active
  elif ! ort_drm_is_broken_vgem; then
    export WANGP_ORT_DRM_STATUS=ok
  fi
fi

exec "$@"
