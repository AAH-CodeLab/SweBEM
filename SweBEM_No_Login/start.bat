@echo off
REM ============================================================
REM  SweBEM - one-click launcher (sequential startup)
REM  1) Start backend, wait until it actually responds
REM  2) Start frontend, wait until it actually responds
REM  3) Open the app in the browser
REM ============================================================
title SweBEM Launcher
cd /d "%~dp0"

echo ============================================================
echo   Starting SweBEM
echo   Backend  : http://localhost:8000
echo   Frontend : http://swebem.local:3000  (or http://localhost:3000)
echo ============================================================
echo.

REM --- [1/3] Backend -------------------------------------------------
echo [1/3] Starting backend...
start "SweBEM Backend" cmd /k call "%~dp0run-backend.cmd"

echo       Waiting for backend to respond (http://localhost:8000)...
set /a tries=0
:waitbackend
curl.exe -s -o nul --max-time 3 http://localhost:8000/
if not errorlevel 1 goto backendup
set /a tries+=1
if %tries% geq 60 (
  echo       WARNING: backend did not respond after ~2 min - continuing anyway.
  goto backendup
)
timeout /t 2 /nobreak >nul
goto waitbackend
:backendup
echo       Backend is ready.
echo.

REM --- [2/3] Frontend -----------------------------------------------
echo [2/3] Starting frontend...
start "SweBEM Frontend" cmd /k call "%~dp0run-frontend.cmd"

echo       Waiting for frontend to respond (http://localhost:3000)...
echo       (first launch compiles the app - this can take a minute)
REM Accept ONLY a real HTTP response (curl exit 0). A generous --max-time lets a
REM single request ride through the first-time compile instead of being aborted
REM mid-compile. While the port is still closed, curl fails fast and we retry.
set /a tries=0
:waitfrontend
curl.exe -s -o nul --connect-timeout 3 --max-time 180 http://localhost:3000/
if not errorlevel 1 goto frontendup
set /a tries+=1
if %tries% geq 40 (
  echo       WARNING: frontend did not respond - opening browser anyway.
  goto frontendup
)
timeout /t 3 /nobreak >nul
goto waitfrontend
:frontendup
echo       Frontend is ready.
echo.

REM --- [3/3] Open the app -------------------------------------------
echo [3/3] Opening the app in your browser...
REM Use the pretty hostname if it has been added to the hosts file, else fall back.
findstr /i /c:"swebem.local" "%SystemRoot%\System32\drivers\etc\hosts" >nul 2>&1
if not errorlevel 1 (
  start "" http://swebem.local:3000
) else (
  echo       Tip: run setup-hostname.bat as administrator to enable http://swebem.local:3000
  start "" http://localhost:3000
)

echo.
echo Done. Close the two server windows to stop everything.
timeout /t 5 /nobreak >nul
