#!/usr/bin/env bash
# WanGP-Lab cockpit UI (WSL). Profile 4 + sage by default.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"
PROFILE="${WANGP_PROFILE:-4}"
ATTN="${WANGP_ATTENTION:-sage}"
PORT="${WANGP_PORT:-7860}"
OPEN_BROWSER="${WANGP_OPEN_BROWSER:-1}"
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --attention) ATTN="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --no-browser) OPEN_BROWSER=0; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help)
      cat <<EOF
Usage: bash suite/scripts/start_wangp_ui.sh [options]

  --profile N       mmgp profile (default: ${WANGP_PROFILE:-4})
  --attention MODE  sage|sdpa|auto|... (default: ${WANGP_ATTENTION:-sage})
  --port N          Gradio port (default: 7860)
  --no-browser      do not try to open a browser
  --force           start even if another wgp/move job is running

UI: http://localhost:${PORT}
EOF
      exit 0
      ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done

# lab hygiene (quiet) before UI
if [[ -f "$ROOT/suite/scripts/lab_hygiene.sh" ]]; then
  bash "$ROOT/suite/scripts/lab_hygiene.sh" --quiet || true
fi

cd "$WANGP_ROOT"
if [[ ! -x .venv/bin/python ]]; then
  echo "missing wangp venv: $WANGP_ROOT/.venv" >&2
  exit 2
fi
if [[ ! -d plugins/wan2gp-lab-bridge ]]; then
  echo "Lab Bridge missing — run: bash suite/scripts/install_bridge.sh" >&2
  exit 2
fi

if [[ "$FORCE" != "1" ]]; then
  if pgrep -f 'wgp\.py' >/dev/null 2>&1; then
    echo "WanGP UI already running (wgp.py). Open http://localhost:${PORT}" >&2
    echo "Use --force to start another instance." >&2
    exit 1
  fi
  if pgrep -f 'wan2gp_move_e01|_run_api\.py' >/dev/null 2>&1; then
    echo "Headless Move job still owns the GPU. Wait or stop it before UI." >&2
    echo "  pgrep -af 'wan2gp_move|_run_api|wgp'" >&2
    echo "Override: --force" >&2
    exit 1
  fi
fi

if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | grep -qE ":${PORT}\\b"; then
  echo "Port ${PORT} already in use — UI may already be up: http://localhost:${PORT}" >&2
  if [[ "$FORCE" != "1" ]]; then
    exit 1
  fi
fi

PY="$WANGP_ROOT/.venv/bin/python"
# activate for PATH deps (ffmpeg libs etc.) but always exec absolute PY
# shellcheck source=/dev/null
source .venv/bin/activate 2>/dev/null || true
export AIIMGSEQ_LAB_ROOT="$LAB_MOTOR_ROOT"
export AIIMGSEQ_WANGP_ROOT="$WANGP_ROOT"
export WANGP_LAB_ROOT WANGP_LAB_CACHE WANGP_LAB_EXPERIMENTS WANGP_LAB_OUTPUTS

# WanGP reads SERVER_NAME / SERVER_PORT (not GRADIO_SERVER_*). Default listen all ifaces.
export SERVER_NAME="${SERVER_NAME:-0.0.0.0}"
export SERVER_PORT="${SERVER_PORT:-$PORT}"
export GRADIO_SERVER_NAME="${GRADIO_SERVER_NAME:-$SERVER_NAME}"
export GRADIO_SERVER_PORT="${GRADIO_SERVER_PORT:-$SERVER_PORT}"
# Allow Lab Bridge to show stills/tracks/previews from suite paths
export GRADIO_ALLOWED_PATHS="${GRADIO_ALLOWED_PATHS:-${WANGP_LAB_ROOT}/data/cache/wanmove,${WANGP_LAB_ROOT}/_outputs,${WANGP_LAB_ROOT}/data/experiments}"

echo "WanGP-Lab UI | profile=$PROFILE attention=$ATTN port=$SERVER_PORT bind=$SERVER_NAME"
echo "  suite  $WANGP_LAB_ROOT"
echo "  wangp  $WANGP_ROOT"
echo "  gate   $LAB_MOTOR_ROOT  (pose_gate venv)"
echo "  cache  $WANGP_LAB_CACHE"
echo "  python $PY"
STACK_FP="$("$PY" -c 'import sys,torch; print("py%s.%s torch%s" % (sys.version_info.major, sys.version_info.minor, torch.__version__))' 2>/dev/null || echo '?')"
echo "  stack  $STACK_FP"
echo "  open   http://localhost:${SERVER_PORT}  (Windows browser OK)"
echo "  Lab Bridge · mission assets under data/cache/wanmove/"

if [[ "$OPEN_BROWSER" == "1" ]]; then
  (
    sleep 4
    if command -v wslview >/dev/null 2>&1; then
      wslview "http://localhost:${SERVER_PORT}" >/dev/null 2>&1 || true
    elif command -v powershell.exe >/dev/null 2>&1; then
      powershell.exe -NoProfile -Command "Start-Process 'http://localhost:${SERVER_PORT}'" >/dev/null 2>&1 || true
    fi
  ) &
fi

# Explicit CLI: --listen → 0.0.0.0; --server-port (wgp ignores bare GRADIO_* alone)
WGP_ARGS=(wgp.py --profile "$PROFILE" --attention "$ATTN" --server-port "$SERVER_PORT")
if [[ "$SERVER_NAME" == "0.0.0.0" || "$SERVER_NAME" == "*" ]]; then
  WGP_ARGS+=(--listen)
else
  WGP_ARGS+=(--server-name "$SERVER_NAME")
fi

# ORT WSL DRM: empty fake vgem card0 so discovery does not WARN (see suite/docs/ORT_WSL_DRM.md)
WRAP="$ROOT/suite/scripts/with_ort_wsl_env.sh"
if [[ -f "$WRAP" ]]; then
  exec bash "$WRAP" -- "$PY" "${WGP_ARGS[@]}"
fi
exec "$PY" "${WGP_ARGS[@]}"
