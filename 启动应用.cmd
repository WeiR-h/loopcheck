@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run install.ps1 first.
  pause
  exit /b 1
)
echo LoopCheck: http://127.0.0.1:8791
".venv\Scripts\python.exe" run.py
pause
