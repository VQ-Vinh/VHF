@echo off
setlocal
chcp 65001 >nul
title PRANA ELEX - Build

set "ROOT=%~dp0..\..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "SPEC=%~dp0PRANA_ELEX.spec"
set "VENV=%ROOT%\.venv\windows"
set "WORK_DIR=%ROOT%\build\windows"
set "DIST_DIR=%ROOT%\dist\windows"
set "RELEASE_DIR=%ROOT%\release\windows"
cd /d "%ROOT%"

if /I not "%OS%"=="Windows_NT" (
    echo [ERROR] buildwin.bat can only run on Windows.
    exit /b 1
)

if not exist "%VENV%\Scripts\python.exe" (
    echo [1/7] Creating virtual environment...
    python -m venv "%VENV%"
    if errorlevel 1 goto :error
) else (
    echo [1/7] Virtual environment ready.
)

echo [2/7] Installing project dependencies...
"%VENV%\Scripts\python.exe" -m pip install -e "%ROOT%"
if errorlevel 1 goto :error

echo [3/7] Installing PyInstaller...
"%VENV%\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 goto :error

echo [CHECK] Validating production client configuration...
"%VENV%\Scripts\python.exe" "%ROOT%\scripts\packaging\common\validate_client_config.py" "%ROOT%\config\profiles\windows-device.toml"
if errorlevel 1 goto :error

echo [4/7] Cleaning previous build...
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"

echo [5/7] Building PRANA_ELEX.exe...
"%VENV%\Scripts\python.exe" -m PyInstaller --noconfirm --clean --workpath "%WORK_DIR%" --distpath "%DIST_DIR%" "%SPEC%"
if errorlevel 1 goto :error

echo [6/7] Validating release bundle...
"%VENV%\Scripts\python.exe" "%ROOT%\scripts\packaging\common\validate_release.py" --platform windows --bundle "%DIST_DIR%\PRANA_ELEX"
if errorlevel 1 goto :error

for /f "delims=" %%V in ('""%VENV%\Scripts\python.exe" "%ROOT%\scripts\packaging\common\project_metadata.py" --field version"') do set "APP_VERSION=%%V"
if not defined APP_VERSION (
    echo [ERROR] Could not read project version from pyproject.toml.
    goto :error
)

echo [7/7] Building Windows installer...
set "ISCC="
for %%I in (ISCC.exe) do set "ISCC=%%~$PATH:I"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if defined ISCC (
    "%ISCC%" /DMyAppVersion=%APP_VERSION% "%ROOT%\scripts\packaging\windows\installer\PRANA_ELEX.iss"
    if errorlevel 1 goto :error
    echo [OK] Installer: %RELEASE_DIR%\PRANA_ELEX_Setup_%APP_VERSION%_x64.exe
) else (
    echo [SKIP] Inno Setup 6 not found. Portable release is still ready.
    echo [INFO] Install Inno Setup 6, then run build.bat again to create the installer.
)

echo.
echo [OK] Output: %DIST_DIR%\PRANA_ELEX\PRANA_ELEX.exe
echo [SECURITY] The desktop release uses PRANA API and contains no Google credentials.
pause
exit /b 0

:error
echo.
echo [ERROR] Clean build failed.
pause
exit /b 1
