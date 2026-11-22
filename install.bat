@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================================
echo   Personal AI Workspace - Windows Local Setup
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.12+ was not found in PATH.
    echo Please install Python 3.12+ from https://www.python.org/downloads/
    exit /b 1
)

where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js / npm was not found in PATH.
    echo Please install Node.js LTS from https://nodejs.org/
    exit /b 1
)

echo [1/5] Creating Python virtual environment in backend\.venv ...
if not exist "backend\.venv\Scripts\python.exe" (
    python -m venv "backend\.venv"
    if errorlevel 1 (
        echo [ERROR] Failed to create Python virtual environment.
        exit /b 1
    )
) else (
    echo       Virtual environment already exists. Skipping creation.
)

echo [2/5] Installing Python backend dependencies ...
"backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    exit /b 1
)
"backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    exit /b 1
)

echo [3/5] Preparing local environment files ...
if not exist "backend\.env" (
    copy "backend\.env.example" "backend\.env" >nul
    echo       Created backend\.env from backend\.env.example
) else (
    echo       backend\.env already exists. Keeping existing file.
)

if not exist "frontend\.env" (
    copy "frontend\.env.example" "frontend\.env" >nul
    echo       Created frontend\.env from frontend\.env.example
) else (
    echo       frontend\.env already exists. Keeping existing file.
)

echo [4/5] Initializing SQLite database with Alembic ...
pushd "backend"
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
    popd
    echo [ERROR] Alembic database initialization failed.
    exit /b 1
)
popd

echo [5/5] Installing frontend Node.js dependencies ...
pushd "frontend"
call npm.cmd install
if errorlevel 1 (
    popd
    echo [ERROR] Frontend npm install failed.
    exit /b 1
)
popd

echo.
echo ============================================================
echo   Installation complete!
echo   Run start.bat to launch Personal AI Workspace locally.
echo ============================================================
exit /b 0
