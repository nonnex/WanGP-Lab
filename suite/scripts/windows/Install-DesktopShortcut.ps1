# Creates Desktop + Start Menu shortcut for WanGP-Lab UI
# Run once from Windows:
#   powershell -ExecutionPolicy Bypass -File \\wsl$\Ubuntu\home\nick\AI\Projects\WanGP-Lab\suite\scripts\windows\Install-DesktopShortcut.ps1
# Or from WSL:
#   bash suite/scripts/install_windows_shortcut.sh

$ErrorActionPreference = "Stop"

$suiteWin = "\\wsl$\Ubuntu\home\nick\AI\Projects\WanGP-Lab"
$bat = Join-Path $suiteWin "suite\scripts\windows\Start-WanGP-Lab.bat"
if (-not (Test-Path -LiteralPath $bat)) {
  throw "Launcher not found: $bat (is WSL Ubuntu running?)"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$lnkPath = Join-Path $desktop "WanGP-Lab.lnk"
$lnkStart = Join-Path $startMenu "WanGP-Lab.lnk"

$w = New-Object -ComObject WScript.Shell
foreach ($path in @($lnkPath, $lnkStart)) {
  $s = $w.CreateShortcut($path)
  $s.TargetPath = $bat
  $s.WorkingDirectory = Split-Path $bat -Parent
  $s.WindowStyle = 1
  $s.Description = "WanGP-Lab cockpit (WSL) - http://localhost:7860"
  $s.IconLocation = "C:\Windows\System32\shell32.dll,13"
  $s.Save()
  Write-Host "Created $path"
}

Write-Host ""
Write-Host "Double-click Desktop: WanGP-Lab"
Write-Host "UI: http://localhost:7860"
