@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe start.py
) else (
  echo Once README.md icindeki kurulumu tamamlayin.
  pause
)
