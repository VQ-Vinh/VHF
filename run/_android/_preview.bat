@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\..\apps\android\scripts\preview.ps1" %*
exit /b %ERRORLEVEL%
