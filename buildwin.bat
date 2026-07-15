@echo off
call "%~dp0scripts\packaging\windows\build.bat" %*
exit /b %errorlevel%
