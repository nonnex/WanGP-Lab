# shellcheck shell=bash
# ORT + WSL DRM discovery helpers (source from suite scripts).
#
# Root cause (not a missing GPU):
#   WSL2 exposes platform vgem as /sys/class/drm/card0. That node has no
#   device/vendor sysfs attribute (not a PCI card). ORT ≥1.24 Linux device
#   discovery reads cardN/device/vendor; on failure it logs WARNING and may
#   abort DRM scan. Real GPU here is dxgkrnl (Microsoft 0x1414) + CUDA via
#   /dev/dxg — CUDAExecutionProvider still works; the message is noisy, not fatal.
#
# Clean handling (no stderr filter):
#   Hide broken DRM tree in a user+mount namespace (empty tmpfs on
#   /sys/class/drm) so ORT skips DRM and uses PCI/EP registration without
#   the ReadFileContents warning. Torch/CUDA keep working via /dev/dxg.
#
# Upstream: microsoft/onnxruntime#26763, PR #29858 (skip non-PCI DRM cards).
# Until a wheel with that skip is pinned here, namespace is the host-side fix.

ort_drm_vendor_path() {
  echo "/sys/class/drm/card0/device/vendor"
}

ort_drm_is_broken_vgem() {
  # True when card0 exists, points at vgem/platform, and vendor file is absent.
  local card="/sys/class/drm/card0"
  local vendor="$card/device/vendor"
  [[ -e "$card" ]] || return 1
  [[ -e "$vendor" ]] && return 1
  local dev
  dev="$(readlink -f "$card/device" 2>/dev/null || true)"
  if [[ "$dev" == *"/vgem"* ]] || [[ "$dev" == *"/simple-framebuffer"* ]]; then
    return 0
  fi
  # card0 present, no vendor → treat as broken discovery target
  [[ -e "$card/device" ]] && return 0
  return 1
}

ort_drm_diagnose() {
  local card="/sys/class/drm/card0"
  echo "ORT/WSL DRM preflight"
  if [[ ! -e /sys/class/drm ]]; then
    echo "  /sys/class/drm: missing"
    return 0
  fi
  echo "  drm cards: $(ls -1 /sys/class/drm 2>/dev/null | tr '\n' ' ')"
  if [[ -e "$card" ]]; then
    echo "  card0 → $(readlink -f "$card" 2>/dev/null || echo '?')"
    echo "  device → $(readlink -f "$card/device" 2>/dev/null || echo '?')"
    if [[ -e "$card/device/vendor" ]]; then
      echo "  vendor: $(cat "$card/device/vendor" 2>/dev/null)"
    else
      echo "  vendor: ABSENT (ORT DRM probe will WARN on this host)"
    fi
  fi
  if command -v nvidia-smi >/dev/null 2>&1; then
    echo "  nvidia-smi: $(nvidia-smi -L 2>/dev/null | head -1)"
  else
    echo "  nvidia-smi: missing"
  fi
  if [[ -e /dev/dxg ]]; then
    echo "  /dev/dxg: present (WSL CUDA path)"
  else
    echo "  /dev/dxg: missing"
  fi
  if ort_drm_is_broken_vgem; then
    echo "  status: BROKEN_VGEM — use with_ort_wsl_env.sh / start_wangp_ui.sh"
  else
    echo "  status: OK (vendor readable or no fake card0)"
  fi
}

ort_drm_unshare_available() {
  command -v unshare >/dev/null 2>&1 || return 1
  # probe: can we create userns + mount empty drm?
  unshare -rm true 2>/dev/null
}

# Re-exec current command under user+mount ns with empty /sys/class/drm.
# Call only from a wrapper that has not yet imported onnxruntime.
ort_drm_exec_with_clean_sysfs() {
  if [[ "${WANGP_ORT_DRM_NS:-}" == "1" ]]; then
    # already inside
    return 1
  fi
  if [[ "${WANGP_ORT_DRM_NS:-}" == "0" ]] || [[ "${WANGP_ORT_DRM_NS:-}" == "off" ]]; then
    return 1
  fi
  ort_drm_is_broken_vgem || return 1
  ort_drm_unshare_available || return 1

  export WANGP_ORT_DRM_NS=1
  export WANGP_ORT_DRM_STATUS=broken_vgem_ns
  # shellcheck disable=SC2093
  exec unshare -rm bash -c '
    set -euo pipefail
    mount -t tmpfs -o size=1M,mode=755,nodev,nosuid none /sys/class/drm
    # Keep a marker so status tools know why drm is empty
    echo "wangp-ort-wsl-drm-ns" > /sys/class/drm/README.wangp 2>/dev/null || true
    exec "$@"
  ' bash "$@"
}
