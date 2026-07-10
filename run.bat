@echo off
cd /d "%~dp0"

:: Kiểm tra venv
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo [!] Run setup.bat first, then try again.
    pause
    exit /b 1
)

:: Load .env
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
)

:: Kiểm tra API key
if "%GEMINI_API_KEY%"=="" (
    echo [WARNING] GEMINI_API_KEY is empty.
    echo [!] Edit .env and set your GEMINI_API_KEY
    echo.
)

set PYTHONPATH=%~dp0
"%~dp0venv\Scripts\python.exe" -u "%~dp0vhf_processor\main.py" %*
