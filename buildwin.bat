@echo off
call "%~dp0apps\windows\build.bat" %*
exit /b %errorlevel%
