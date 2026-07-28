#!/usr/bin/env bash
# Create Windows Desktop + Start Menu shortcut for WanGP-Lab UI
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PS1="$ROOT/suite/scripts/windows/Install-DesktopShortcut.ps1"
if [[ ! -f "$PS1" ]]; then
  echo "missing $PS1" >&2
  exit 2
fi
# Prefer UNC path so PowerShell resolves the script on Windows side
UNC='\\wsl$\Ubuntu\home\nick\AI\Projects\WanGP-Lab\suite\scripts\windows\Install-DesktopShortcut.ps1'
if command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$UNC"
else
  echo "powershell.exe not found (need Windows host)" >&2
  exit 2
fi
