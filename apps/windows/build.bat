@echo off
call "%~dp0packaging\build.bat" %*
exit /b %errorlevel%
