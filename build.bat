@echo off
chcp 65001 >nul
title PRANA ELEX — Build

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Run setup.bat first.
    pause
    exit /b 1
)

echo [1/3] Installing PyInstaller...
call .\venv\Scripts\pip.exe install pyinstaller >nul 2>&1

echo [2/3] Cleaning old dist...
if exist "dist\PRANA_ELEX" rmdir /s /q "dist\PRANA_ELEX"
if exist "dist\PRANA_ELEX.exe" del "dist\PRANA_ELEX.exe"

echo [3/3] Building PRANA_ELEX.exe (cached build/)...
call .\venv\Scripts\pyinstaller.exe PRANA_ELEX.spec

echo.
echo Done! Output: dist\PRANA_ELEX\PRANA_ELEX.exe
pause
