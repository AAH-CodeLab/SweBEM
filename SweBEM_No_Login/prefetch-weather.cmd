@echo off
REM ============================================================
REM  Download every selectable weather (EPW) file into
REM  Backend\weather_files so simulations work offline (without
REM  a live connection to climate.onebuilding.org).
REM  Run this once with internet; re-run anytime to fill gaps.
REM ============================================================
title SweBEM weather prefetch
cd /d "%~dp0Backend"

echo Ensuring dependencies...
python -m pip install -q requests

echo.
python prefetch_weather.py

echo.
pause
