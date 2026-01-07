@echo off
setlocal
cd /d "%~dp0"

where pyinstaller >nul 2>&1
if errorlevel 1 (
  echo PyInstaller not found. Installing with: python -m pip install pyinstaller
  python -m pip install pyinstaller
  if errorlevel 1 (
    echo Failed to install PyInstaller. Please install it manually and retry.
    pause
    exit /b 1
  )
)

python -m PyInstaller --clean --noconfirm --onefile --windowed --name "av-track-merger" ^
  --add-binary "ffmpeg\\bin\\ffmpeg.exe;ffmpeg\\bin" ^
  --add-binary "ffmpeg\\bin\\ffprobe.exe;ffmpeg\\bin" ^
  app.py

if exist build rmdir /s /q build
if exist __pycache__ rmdir /s /q __pycache__
if exist app.spec del /q app.spec

echo.
echo Build finished. Check dist\\av-track-merger.exe
pause
