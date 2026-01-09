@echo off
setlocal
title Install Dependencies (venv)

cd /d "%~dp0"

echo ========================================
echo   Installing Dependencies (venv)
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
  echo Failed to create venv. Please check your Python installation.
  echo.
  pause
  exit /b 1
)

echo Installing Python packages...
echo.
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
pause
