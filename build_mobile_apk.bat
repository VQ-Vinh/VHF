@echo off
echo [PRANA] Building an APK for a physical Android device...
call "%~dp0buildapp.bat" -PhysicalDevice %*
exit /b %errorlevel%
