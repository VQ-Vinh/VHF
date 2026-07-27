@echo off
call "%~dp0services\prana_api\run-dev.bat" %*
exit /b %errorlevel%
