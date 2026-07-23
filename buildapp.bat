@echo off
call "%~dp0apps\android\build.bat" %*
exit /b %errorlevel%
