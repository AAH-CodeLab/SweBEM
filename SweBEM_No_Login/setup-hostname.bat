@echo off
REM ============================================================
REM  One-time setup: map swebem.local -> 127.0.0.1 so the app is
REM  reachable at http://swebem.local:3000
REM
REM  RIGHT-CLICK this file and choose "Run as administrator".
REM  (Editing the Windows hosts file requires admin rights.)
REM ============================================================
title SweBEM hostname setup

REM Require administrator rights.
net session >nul 2>&1
if errorlevel 1 (
  echo.
  echo   This script must be run as Administrator.
  echo   Right-click setup-hostname.bat and choose "Run as administrator".
  echo.
  pause
  exit /b 1
)

set "HOSTS=%SystemRoot%\System32\drivers\etc\hosts"

findstr /i /c:"swebem.local" "%HOSTS%" >nul 2>&1
if not errorlevel 1 (
  echo swebem.local is already in the hosts file - nothing to do.
) else (
  echo.>> "%HOSTS%"
  echo 127.0.0.1 swebem.local>> "%HOSTS%"
  echo Added: 127.0.0.1 swebem.local
)

echo.
echo Done. The app is now reachable at:  http://swebem.local:3000
echo (Start it with start.bat if it is not already running.)
echo.
pause
