#!/usr/bin/env bash
# Compat wrapper → start_wangp_ui.sh (preferred entrypoint)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec bash "$ROOT/suite/scripts/start_wangp_ui.sh" "$@"
