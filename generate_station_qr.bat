@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "PROVISION_EXE=%PROJECT_ROOT%.venv\dev\Scripts\prana-station-provision.exe"
set "STATION_CONFIG=%PROJECT_ROOT%apps\windows\config\default.toml"
set "QR_OUTPUT=%PROJECT_ROOT%stations"

if not exist "%PROVISION_EXE%" (
    echo [ERROR] Station environment is not ready.
    echo Run scripts\setup\setup.bat first.
    exit /b 1
)

if not exist "%STATION_CONFIG%" (
    echo [ERROR] Station config not found:
    echo %STATION_CONFIG%
    exit /b 1
)

echo Generating PRANA ELEX Station QR label...
echo Output: %QR_OUTPUT%

"%PROVISION_EXE%" --config "%STATION_CONFIG%" --output "%QR_OUTPUT%"
if errorlevel 1 (
    echo [ERROR] QR generation failed.
    exit /b 1
)

echo [OK] QR labels are available in:
echo %QR_OUTPUT%
endlocal
