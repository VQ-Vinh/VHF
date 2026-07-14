@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo [!] Run setup.bat first, then try again.
    pause
    exit /b 1
)

set "PYTHONPATH=%~dp0src"

if /I "%~1"=="quiet" (
    start "" "%~dp0venv\Scripts\pythonw.exe" -c "from prana_elex.ui.app import run_app; run_app()"
    exit /b 0
)

echo [DEV] Starting PRANA ELEX from source...
echo [DEV] Press Ctrl+C to stop. Use: run_dev.bat quiet  ^(no console^)
echo.

"%~dp0venv\Scripts\python.exe" -c "from prana_elex.ui.app import run_app; run_app()"
exit /b %errorlevel%
