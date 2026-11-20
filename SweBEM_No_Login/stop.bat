@echo off
REM ============================================================
REM  SweBEM - stop both servers.
REM  Finds whatever is listening on the backend/frontend ports
REM  and terminates it (with child processes). Does NOT touch
REM  unrelated python/node processes.
REM ============================================================
title SweBEM Stop

echo ============================================================
echo   Stopping SweBEM
echo ============================================================
echo.

call :killport 8000 Backend
call :killport 3000 Frontend

echo.
echo Done. You can close this window.
timeout /t 4 /nobreak >nul
exit /b

REM ---- :killport <port> <name> -------------------------------
:killport
set "PORT=%~1"
set "NAME=%~2"
set "FOUND="
for /f "tokens=5" %%A in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%PORT% "') do (
  echo Stopping %NAME% on port %PORT% ^(PID %%A^)...
  taskkill /PID %%A /T /F >nul 2>&1
  set "FOUND=1"
)
if not defined FOUND echo No %NAME% found running on port %PORT%.
exit /b
