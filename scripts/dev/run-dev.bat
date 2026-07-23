@echo off
echo [DEPRECATED] Use run_dev.bat from the repository root.
call "%~dp0..\..\apps\windows\run.bat" %*
exit /b %errorlevel%
