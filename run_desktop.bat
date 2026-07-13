@echo off
cd /d "%~dp0"

:: Check venv
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo [!] Run setup.bat first, then try again.
    pause
    exit /b 1
)

set PYTHONPATH=%~dp0src
"%~dp0venv\Scripts\python.exe" -u -m prana_elex.app.desktop %*
exit /b %errorlevel%