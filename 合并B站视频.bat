@echo off
chcp 65001 >nul
cd /d "%~dp0"

python "%~dp0合并B站视频.py"

pause
