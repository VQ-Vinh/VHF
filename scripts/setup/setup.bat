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

if exist "%ROOT%\.venv\dev\Scripts\python.exe" (
    echo [*] Station environment already exists, skipping creation...
) else (
    echo [*] Creating Station environment...
    python -m venv "%ROOT%\.venv\dev"
    if errorlevel 1 exit /b 1
)

echo [*] Installing Station dependencies...
"%ROOT%\.venv\dev\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%ROOT%\.venv\dev\Scripts\python.exe" -m pip uninstall --yes prana-elex-linux >nul 2>&1
"%ROOT%\.venv\dev\Scripts\python.exe" -m pip install --no-build-isolation -e "%ROOT%\packages\prana_core"
if errorlevel 1 exit /b 1
"%ROOT%\.venv\dev\Scripts\python.exe" -m pip install --no-build-isolation -e "%ROOT%\apps\windows"
if errorlevel 1 exit /b 1

if not exist "%ROOT%\.venv\dev\Scripts\prana-station-provision.exe" (
    echo [ERROR] Station provisioning command was not installed.
    exit /b 1
)

if exist "%ROOT%\.venv\backend\Scripts\python.exe" (
    echo [*] Backend environment already exists, skipping creation...
) else (
    echo [*] Creating backend environment...
    python -m venv "%ROOT%\.venv\backend"
    if errorlevel 1 exit /b 1
)

echo [*] Installing API and Admin dependencies...
"%ROOT%\.venv\backend\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%ROOT%\.venv\backend\Scripts\python.exe" -m pip install -r "%ROOT%\services\prana_api\requirements.txt"
if errorlevel 1 exit /b 1
"%ROOT%\.venv\backend\Scripts\python.exe" -m pip install -r "%ROOT%\services\prana_admin\requirements.txt"
if errorlevel 1 exit /b 1

if not exist "%ROOT%\.venv\backend\Scripts\uvicorn.exe" (
    echo [ERROR] Backend API command was not installed.
    exit /b 1
)

if not exist "%ROOT%\VHF_Storage\audio" mkdir "%ROOT%\VHF_Storage\audio"
if not exist "%ROOT%\VHF_Storage\results" mkdir "%ROOT%\VHF_Storage\results"

echo.
echo [OK] Windows setup complete.
echo      Generate Station QR: generate_station_qr.bat
echo      Start Station with Cloud API: enable_station_api.bat
echo      Developer local API mode: enable_station_api.bat -LocalApi
pause
