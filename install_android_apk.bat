@echo off
echo [PRANA] Cai APK len dien thoai Android qua ADB...
call "%~dp0apps\android\install.bat" %*
exit /b %errorlevel%
