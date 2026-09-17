@echo off
rem Start the PRANA ELEX desktop operator console from the dev environment.
rem   run_desktop.bat          with a console window, so errors stay visible
rem   run_desktop.bat quiet    without a console window
rem The real launcher is apps\windows\run.bat; this only forwards to it.
setlocal
call "%~dp0apps\windows\run.bat" %*
set "CODE=%errorlevel%"
if not "%CODE%"=="0" (
    echo.
    echo [ERROR] Desktop app exited with code %CODE%.
    pause
)
exit /b %CODE%
