@echo off
call "%~dp0scripts\packaging\build.bat" %*
exit /b %errorlevel%
