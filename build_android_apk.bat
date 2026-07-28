@echo off
echo [PRANA] Building an APK for a physical Android device...
call "%~dp0apps\android\build.bat" -PhysicalDevice %*
exit /b %errorlevel%
