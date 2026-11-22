# Scripts

Windows startup and setup scripts live at the project root for direct execution:

- `install.bat` — creates `backend\.venv`, installs Python & Node dependencies, prepares `.env` files, and runs Alembic migrations.
- `start.bat` — starts the local FastAPI backend and Vite frontend in visible terminal windows.
- `stop.bat` — terminates the `PAW-Backend` and `PAW-Frontend` windows.

Future phases may add cross-platform maintenance scripts (e.g., macOS `.sh` helpers, backup/export utilities) in this directory.
