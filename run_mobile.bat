@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev\run-mobile.ps1" %*
exit /b %ERRORLEVEL%
