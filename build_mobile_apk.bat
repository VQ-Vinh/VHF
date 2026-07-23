@echo off
echo [DEPRECATED] Use buildapp.bat. Forwarding arguments...
call "%~dp0buildapp.bat" %*
exit /b %errorlevel%
