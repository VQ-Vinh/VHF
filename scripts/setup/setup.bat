@echo off
setlocal enabledelayedexpansion
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"

echo ============================================================
echo   PRANA ELEX - Setup
echo ============================================================
echo.

echo [*] Checking Python version...
python --version 2>nul | findstr /R "3\.1[1-9] 3\.[2-9]" >nul
if errorlevel 1 (
    echo [ERROR] Python 3.11 or newer is required.
    pause
    exit /b 1
)

if exist "%ROOT%\venv\Scripts\python.exe" (
    echo [*] Virtual environment already exists, skipping...
) else (
    echo [*] Creating virtual environment...
    python -m venv "%ROOT%\venv"
    if errorlevel 1 exit /b 1
)

echo [*] Installing dependencies...
"%ROOT%\venv\Scripts\python.exe" -m pip install --upgrade pip
"%ROOT%\venv\Scripts\python.exe" -m pip install -e "%ROOT%"
if errorlevel 1 exit /b 1

if not exist "%ROOT%\data\audio" mkdir "%ROOT%\data\audio"
if not exist "%ROOT%\data\results" mkdir "%ROOT%\data\results"

echo.
echo [OK] Setup complete. Run: run_dev.bat
pause
