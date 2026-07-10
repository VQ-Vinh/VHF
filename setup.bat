@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ============================================================
echo   VHF Radio Processor - Setup
echo ============================================================
echo.

:: 1. Kiểm tra Python >= 3.11
echo [*] Checking Python version...
python --version 2>nul | findstr /R "3\.1[1-9] 3\.[2-9]" >nul
if errorlevel 1 (
    python --version 2>nul
    if !errorlevel! equ 0 (
        echo [ERROR] Python 3.11+ is required. Found:
    ) else (
        echo [ERROR] Python not found or not in PATH.
    )
    echo [!] Install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>nul') do set pyver=%%v
echo [OK] Python %pyver%

:: 2. Tạo virtual environment
if exist "venv\Scripts\python.exe" (
    echo [*] Virtual environment already exists, skipping...
) else (
    echo [*] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

:: 3. Cài dependencies (editable install)
echo [*] Installing dependencies...
"venv\Scripts\python.exe" -m pip install --upgrade pip >nul
"venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (
    echo [ERROR] Dependency installation failed
    pause
    exit /b 1
)
echo [OK] Dependencies installed

:: 4. Tạo thư mục data
if not exist "data\audio" mkdir data\audio 2>nul
if not exist "data\results" mkdir data\results 2>nul
echo [OK] Data directories ready

echo.
echo ============================================================
echo   Setup complete!
echo ============================================================
echo.
echo   Run: run.bat
echo.
pause
