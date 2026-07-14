@echo off
chcp 65001 >nul
title PRANA ELEX - Build

set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "SPEC=%~dp0PRANA_ELEX.spec"
cd /d "%ROOT%"

if not exist "%ROOT%\venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Run scripts\setup\setup.bat first.
    pause
    exit /b 1
)

echo [1/3] Installing PyInstaller...
"%ROOT%\venv\Scripts\python.exe" -m pip install pyinstaller

echo [2/3] Cleaning previous distribution...
if exist "%ROOT%\dist\PRANA_ELEX" rmdir /s /q "%ROOT%\dist\PRANA_ELEX"
if exist "%ROOT%\dist\PRANA_ELEX.exe" del "%ROOT%\dist\PRANA_ELEX.exe"
if exist "%ROOT%\dist\settings.json" del "%ROOT%\dist\settings.json"

echo [3/3] Building PRANA_ELEX.exe...
"%ROOT%\venv\Scripts\python.exe" -m PyInstaller --noconfirm "%SPEC%"
if errorlevel 1 exit /b 1

echo.
echo [OK] Output: %ROOT%\dist\PRANA_ELEX\PRANA_ELEX.exe
pause
