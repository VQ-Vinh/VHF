@echo off
echo [DEPRECATED] build.bat is an alias for buildwin.bat.
echo [INFO] Use buildwin.bat for Windows or ./buildlinux on Raspberry Pi.
call "%~dp0buildwin.bat" %*
exit /b %errorlevel%
