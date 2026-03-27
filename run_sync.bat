@echo off
REM Daily Shopify -> Softland sync. Task Scheduler should run this file.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" main.py
) else (
  python main.py
)
if errorlevel 1 exit /b 1
exit /b 0
