@echo off
cd /d "%~dp0"

:: Kiểm tra venv
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo [!] Run setup.bat first, then try again.
    pause
    exit /b 1
)

set PYTHONPATH=%~dp0
"%~dp0venv\Scripts\python.exe" -u "%~dp0vhf_processor\main.py" %*
exit /b %errorlevel%
