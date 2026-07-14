@echo off
call "%~dp0scripts\dev\run-dev.bat" %*
exit /b %errorlevel%
