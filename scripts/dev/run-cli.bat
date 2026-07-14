@echo off
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"

if not exist "%ROOT%\venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo [!] Run scripts\setup\setup.bat first, then try again.
    pause
    exit /b 1
)

set "PYTHONPATH=%ROOT%\src"
"%ROOT%\venv\Scripts\python.exe" -u -m prana_elex.app.cli %*
exit /b %errorlevel%
