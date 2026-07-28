#!/usr/bin/env bash
# Wrapper → run_move_e01.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$ROOT/suite/tools/run_move_e01.sh" "$@"
