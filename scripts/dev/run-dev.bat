@echo off
echo [DEPRECATED] Use apps\windows\run.bat from the repository root.
call "%~dp0..\..\apps\windows\run.bat" %*
exit /b %errorlevel%
