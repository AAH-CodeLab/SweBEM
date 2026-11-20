@echo off
REM Started by start.bat (or double-click to run the frontend on its own).
title SweBEM Frontend
cd /d "%~dp0Frontend"

if not exist node_modules (
  echo Installing frontend dependencies - first run, this can take a while...
  call npm install
)

echo.
echo Starting frontend on http://localhost:3000 ...
echo (Close this window to stop the frontend.)
echo.
call npm run dev

echo.
echo Frontend has stopped. Press any key to close this window.
pause >nul
