@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PYTHON=%ROOT%\.venv\dev\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo [ERROR] Development environment not found. Run scripts\setup\setup.bat.
    exit /b 1
)
set "PYTHONPATH=%ROOT%\packages\prana_core\src;%ROOT%\apps\windows\src"
if /I "%~1"=="quiet" (
    start "" "%ROOT%\.venv\dev\Scripts\pythonw.exe" -m prana_windows.desktop
    exit /b 0
)
"%PYTHON%" -m prana_windows.desktop
exit /b %errorlevel%
