@echo off
cd /d "%~dp0"
if exist ".env" for /f "usebackq tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
set PYTHONPATH=%~dp0
"%~dp0venv\Scripts\python.exe" -u "%~dp0vhf_processor\main.py" %*
