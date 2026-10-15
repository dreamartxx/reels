@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe cloud\worker.py
pause
