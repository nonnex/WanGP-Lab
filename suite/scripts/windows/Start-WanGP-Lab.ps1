# WanGP-Lab cockpit launcher (Windows PowerShell)
# Desktop shortcut can target this or Start-WanGP-Lab.bat
param(
  [string]$Distro = "Ubuntu",
  [string]$Suite = "/home/nick/AI/Projects/WanGP-Lab",
  [int]$Port = 7860,
  [switch]$Force,
  [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$host.UI.RawUI.WindowTitle = "WanGP-Lab"

Write-Host ""
Write-Host " WanGP-Lab UI  ->  http://localhost:$Port"
Write-Host " Closing this window stops WanGP."
Write-Host ""

if (-not $NoBrowser) {
  Start-Job -ScriptBlock {
    param($p)
    Start-Sleep -Seconds 6
    Start-Process "http://localhost:$p"
  } -ArgumentList $Port | Out-Null
}

$extra = ""
if ($Force) { $extra += " --force" }
if ($NoBrowser) { $extra += " --no-browser" }

$cmd = "cd '$Suite' && bash suite/scripts/start_wangp_ui.sh --port $Port$extra"
& wsl.exe -d $Distro -e bash -lc $cmd
$ec = $LASTEXITCODE
if ($ec -ne 0) {
  Write-Host ""
  Write-Host " Start failed exit=$ec"
  Write-Host " GPU busy? wait for Move, or re-run with -Force"
  if (-not $env:CI) { Read-Host "Press Enter to close" | Out-Null }
}
exit $ec
