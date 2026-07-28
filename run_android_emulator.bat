@echo off
chcp 65001 >nul
call "%~dp0apps\android\run.bat" %*
exit /b %errorlevel%
