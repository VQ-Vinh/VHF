@echo off
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"

if not exist "%ROOT%\.venv\dev\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo [!] Run scripts\setup\setup.bat first, then try again.
    pause
    exit /b 1
)

set "PYTHONPATH=%ROOT%\src"

if /I "%~1"=="quiet" (
    start "" "%ROOT%\.venv\dev\Scripts\pythonw.exe" -c "from prana_elex.ui.app import run_app; run_app()"
    exit /b 0
)

echo [DEV] Starting PRANA ELEX from source...
echo [DEV] Press Ctrl+C to stop. Use: run_dev.bat quiet  ^(no console^)
echo.

"%ROOT%\.venv\dev\Scripts\python.exe" -c "from prana_elex.ui.app import run_app; run_app()"
exit /b %errorlevel%
