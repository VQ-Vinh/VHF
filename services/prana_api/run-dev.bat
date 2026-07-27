@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PYTHON=%ROOT%\.venv\backend\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo [ERROR] Backend environment not found at .venv\backend.
    exit /b 1
)

set "PRANA_API_ENVIRONMENT=development"
set "PRANA_API_GOOGLE_CLOUD_PROJECT=prana-elex-staging-2816"
set "PRANA_API_FIREBASE_PROJECT_ID=prana-elex-staging-2816"
set "PRANA_API_STORAGE_BUCKET=prana-elex-staging-2816-recordings"

cd /d "%ROOT%"
if /I "%~1"=="--no-reload" (
    "%PYTHON%" -m uvicorn services.prana_api.main:app --host 0.0.0.0 --port 8080
) else (
    "%PYTHON%" -m uvicorn services.prana_api.main:app --reload --host 0.0.0.0 --port 8080
)
exit /b %errorlevel%
