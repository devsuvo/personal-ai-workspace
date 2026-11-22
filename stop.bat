@echo off
setlocal

echo Stopping Personal AI Workspace local service windows...

taskkill /FI "WINDOWTITLE eq PAW-Backend*" /T /F >nul 2>&1
if %errorlevel%==0 (
    echo   - Stopped PAW-Backend
) else (
    echo   - PAW-Backend window was not running
)

taskkill /FI "WINDOWTITLE eq PAW-Frontend*" /T /F >nul 2>&1
if %errorlevel%==0 (
    echo   - Stopped PAW-Frontend
) else (
    echo   - PAW-Frontend window was not running
)

echo Done.
exit /b 0
