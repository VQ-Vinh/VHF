@echo off
setlocal
chcp 65001 >nul
title PRANA ELEX - Build

set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "SPEC=%~dp0PRANA_ELEX.spec"
cd /d "%ROOT%"

if not exist "%ROOT%\venv\Scripts\python.exe" (
    echo [1/5] Creating virtual environment...
    python -m venv "%ROOT%\venv"
    if errorlevel 1 goto :error
) else (
    echo [1/5] Virtual environment ready.
)

echo [2/5] Installing project dependencies...
"%ROOT%\venv\Scripts\python.exe" -m pip install -e "%ROOT%"
if errorlevel 1 goto :error

echo [3/5] Installing PyInstaller...
"%ROOT%\venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 goto :error

echo [4/5] Cleaning previous build...
if exist "%ROOT%\build" rmdir /s /q "%ROOT%\build"
if exist "%ROOT%\dist\PRANA_ELEX" rmdir /s /q "%ROOT%\dist\PRANA_ELEX"
if exist "%ROOT%\dist\PRANA_ELEX.exe" del "%ROOT%\dist\PRANA_ELEX.exe"
if exist "%ROOT%\dist\settings.json" del "%ROOT%\dist\settings.json"

echo [5/5] Building PRANA_ELEX.exe...
"%ROOT%\venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "%SPEC%"
if errorlevel 1 goto :error

echo.
echo [OK] Output: %ROOT%\dist\PRANA_ELEX\PRANA_ELEX.exe
echo [NOTE] Copy .secrets\gcs-service-account.json beside the EXE before deployment.
pause
exit /b 0

:error
echo.
echo [ERROR] Clean build failed.
pause
exit /b 1
