@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev\enable-station.ps1" %*
exit /b %errorlevel%
