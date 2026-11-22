# Installation Guide — Personal AI Workspace (v1.0.0)

Personal AI Workspace runs completely locally on your own computer. Each computer (Windows PC or MacBook) maintains its own independent SQLite database, encrypted API credentials, uploaded files, and chat history.

---

## Option 1: Standalone Windows Desktop App (`.exe`)

1. Run `dist\PersonalAIWorkspace.exe` (or install using `PersonalAIWorkspace-Setup-1.0.0.exe` built via Inno Setup).
2. On first launch, the app automatically initializes your local SQLite database at:
   `%LOCALAPPDATA%\PersonalAIWorkspace\storage\database\personal_ai_workspace.db`
3. Your standalone desktop window opens automatically—no Node.js or Python installation required on the target machine.

---

## Option 2: Run from Source on Windows

### Prerequisites
- Python 3.12+
- Node.js 20+

### Steps
```bat
install.bat
start.bat
```
Open `http://localhost:5173`. Stop with `stop.bat`.

---

## Option 3: Run from Source on macOS (Apple Silicon & Intel)

### Prerequisites
- Python 3.12+ (`brew install python@3.12`)
- Node.js 20+ (`brew install node`)

### Steps
```bash
# Backend
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
cp -n backend/.env.example backend/.env
(cd backend && alembic upgrade head)

# Frontend
cp -n frontend/.env.example frontend/.env
(cd frontend && npm install)
```

Launch in two terminals:
```bash
# Terminal 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2
cd frontend && npm run dev
```
Open `http://localhost:5173`.

---

## Updating Safely (Preserving User Data)

1. Pull or download the new release.
2. Create a backup first via **Settings → Data Backup → Create Backup**.
3. Re-run `install.bat` (Windows) or `pip install -r backend/requirements.txt && alembic upgrade head` (macOS).
4. Alembic upgrades your SQLite schema in place without deleting conversations, projects, prompts, or encrypted credentials.

---

## Troubleshooting

- **Backend offline in sidebar**: Confirm FastAPI is running on `127.0.0.1:8000` (`http://127.0.0.1:8000/api/v1/health`).
- **Port 8000 already in use**: In packaged desktop mode, `desktop_launcher.py` automatically picks the next free localhost port (`8001–8049`). In source mode, change `BACKEND_PORT` in `backend/.env`.
- **Master key missing error**: Restore your backed-up `storage/secrets/master.key` file; never regenerate it while encrypted credentials exist.
