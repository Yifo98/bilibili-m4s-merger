@echo off
setlocal
title Build EXE (PyInstaller)

cd /d "%~dp0"

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

echo Installing build dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if not exist "settings.json" (
  echo Creating default settings.json...
  >settings.json (
    echo {
    echo   "theme": "light",
    echo   "language": "zh-CN",
    echo   "window_width": 1200,
    echo   "window_height": 760,
    echo   "remember_position": true,
    echo   "max_duration_diff": 5.0,
    echo   "match_strategy": "duration",
    echo   "output_naming": "sequential",
    echo   "filename_template": "{idx}.ATM_{timestamp}.mp4",
    echo   "ffmpeg_threads": 0,
    echo   "copy_codec": true,
    echo   "resolve_safe_mode": true,
    echo   "delete_sources": false,
    echo   "remember_dirs": true,
    echo   "last_input_dir": "",
    echo   "last_output_dir": "",
    echo   "parallel_workers": 4,
    echo   "retry_on_failure": true,
    echo   "max_retries": 2,
    echo   "generate_log": true
    echo }
  )
)

echo.
echo Building EXE...
".venv\Scripts\python.exe" -m PyInstaller ^
  --clean ^
  --noconsole ^
  --onefile ^
  --name "AV Track Merger" ^
  --icon "assets\icon.ico" ^
  --hidden-import "gui.main_window" ^
  --hidden-import "gui" ^
  --collect-submodules "gui" ^
  --collect-submodules "core" ^
  --collect-submodules "services" ^
  --add-data "ffmpeg;ffmpeg" ^
  --add-data "settings.json;." ^
  --add-data "assets;assets" ^
  main.py

if errorlevel 1 (
  echo.
  echo ========================================
  echo   Build Failed
  echo ========================================
  echo.
  pause
  exit /b 1
)

echo.
echo ========================================
echo   Build Complete
echo ========================================
echo Output: dist\AV Track Merger.exe
echo.

echo Cleaning temporary files...
if exist "build" rmdir /s /q "build"
if exist "__pycache__" rmdir /s /q "__pycache__"
del /q "AV Track Merger.spec" >nul 2>&1

pause
