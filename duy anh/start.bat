@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
    echo Chua co moi truong .venv. Xem README.md de cai dat.
    pause
    exit /b 1
)
echo EPU Energy: http://127.0.0.1:5000
".venv\Scripts\python.exe" app.py
pause
