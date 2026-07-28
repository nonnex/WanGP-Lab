@echo off
REM WanGP-Lab cockpit — double-click from Windows (Desktop shortcut target)
setlocal
title WanGP-Lab
set "DISTRO=Ubuntu"
set "SUITE=/home/nick/AI/Projects/WanGP-Lab"
set "PORT=7860"

echo.
echo  WanGP-Lab UI  -^>  http://localhost:%PORT%
echo  Closing this window stops WanGP.
echo.

REM Open browser shortly after start (WSL will also try)
start "" cmd /c "timeout /t 6 /nobreak >nul & start http://localhost:%PORT%"

wsl.exe -d %DISTRO% -e bash -lc "cd '%SUITE%' && bash suite/scripts/start_wangp_ui.sh --port %PORT%"
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo  Start failed exit=%EC%
  echo  If GPU busy: wait for headless Move, or: bash suite/scripts/start_wangp_ui.sh --force
  pause
)
exit /b %EC%
