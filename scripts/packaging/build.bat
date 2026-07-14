@echo off
setlocal
chcp 65001 >nul
title PRANA ELEX - Build

set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "SPEC=%~dp0PRANA_ELEX.spec"
cd /d "%ROOT%"

if not exist "%ROOT%\venv\Scripts\python.exe" (
    echo [1/7] Creating virtual environment...
    python -m venv "%ROOT%\venv"
    if errorlevel 1 goto :error
) else (
    echo [1/7] Virtual environment ready.
)

echo [2/7] Installing project dependencies...
"%ROOT%\venv\Scripts\python.exe" -m pip install -e "%ROOT%"
if errorlevel 1 goto :error

echo [3/7] Installing PyInstaller...
"%ROOT%\venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 goto :error

echo [4/7] Cleaning previous build...
if exist "%ROOT%\build" rmdir /s /q "%ROOT%\build"
if exist "%ROOT%\dist\PRANA_ELEX" rmdir /s /q "%ROOT%\dist\PRANA_ELEX"
if exist "%ROOT%\dist\PRANA_ELEX.exe" del "%ROOT%\dist\PRANA_ELEX.exe"
if exist "%ROOT%\dist\settings.json" del "%ROOT%\dist\settings.json"

echo [5/7] Building PRANA_ELEX.exe...
"%ROOT%\venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "%SPEC%"
if errorlevel 1 goto :error

echo [6/7] Validating release bundle...
"%ROOT%\venv\Scripts\python.exe" "%ROOT%\scripts\packaging\validate_release.py" "%ROOT%\dist\PRANA_ELEX"
if errorlevel 1 goto :error

echo [7/7] Building Windows installer...
set "ISCC="
for %%I in (ISCC.exe) do set "ISCC=%%~$PATH:I"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if defined ISCC (
    "%ISCC%" "%ROOT%\scripts\installer\PRANA_ELEX.iss"
    if errorlevel 1 goto :error
    echo [OK] Installer: %ROOT%\release\PRANA_ELEX_Setup_1.0.0_x64.exe
) else (
    echo [SKIP] Inno Setup 6 not found. Portable release is still ready.
    echo [INFO] Install Inno Setup 6, then run build.bat again to create the installer.
)

echo.
echo [OK] Output: %ROOT%\dist\PRANA_ELEX\PRANA_ELEX.exe
echo [SECURITY] Google service-account credentials are not included in the release.
pause
exit /b 0

:error
echo.
echo [ERROR] Clean build failed.
pause
exit /b 1
