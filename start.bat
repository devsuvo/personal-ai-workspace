@echo off
setlocal

cd /d "%~dp0"

echo ============================================================
echo   Personal AI Workspace - Starting Local Services
echo ============================================================
echo.

if not exist "backend\.venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found at backend\.venv
    echo Please run install.bat first.
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo [ERROR] Frontend dependencies not found at frontend\node_modules
    echo Please run install.bat first.
    exit /b 1
)

echo [1/3] Checking SQLite migrations ...
pushd "backend"
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
    popd
    echo [ERROR] Database migration check failed.
    exit /b 1
)
popd

echo [2/3] Launching FastAPI backend on http://127.0.0.1:8000 ...
start "PAW-Backend" cmd /k "cd /d "%~dp0backend" && call .venv\Scripts\activate.bat && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [3/3] Launching Vite frontend on http://127.0.0.1:5173 ...
start "PAW-Frontend" cmd /k "cd /d "%~dp0frontend" && npm.cmd run dev"

echo.
echo Services are starting in separate terminal windows so logs and errors stay visible:
echo   - Frontend: http://localhost:5173
echo   - Backend:  http://127.0.0.1:8000/api/v1/health
echo   - API Docs: http://127.0.0.1:8000/api/v1/docs
echo.
echo Run stop.bat or close the service windows to stop the application.
exit /b 0
