@echo off
REM Started by start.bat (or double-click to run the backend on its own).
title SweBEM Backend
cd /d "%~dp0Backend"

echo Ensuring Python dependencies are installed...
python -m pip install -q -r requirements.txt python-multipart

echo.
echo Starting backend on http://localhost:8000 ...
echo (Close this window to stop the backend.)
echo.
python api_server.py

echo.
echo Backend has stopped. Press any key to close this window.
pause >nul
