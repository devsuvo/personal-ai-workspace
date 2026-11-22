# Windows Production Build Guide (v1.0.0)

This guide explains how to build the standalone Windows executable (`PersonalAIWorkspace.exe`) and the Inno Setup Windows installer (`PersonalAIWorkspace-Setup-1.0.0.exe`).

## Prerequisites (Build Machine)

- Windows 10 or Windows 11 (x64)
- Python 3.12+ with `backend\.venv` configured
- Node.js 20+
- PyInstaller (`pip install pyinstaller==6.13.0`)
- Optional for `.exe` Setup Wizard: [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`ISCC.exe`)

## Step 1: Build Frontend Production Assets

```bat
cd frontend
npm.cmd run build
cd ..
```

## Step 2: Generate Multi-Resolution Windows Icon

```bat
backend\.venv\Scripts\python.exe packaging\generate_icons.py
```

Creates `packaging\icons\app_icon.ico` (16–256px) and `packaging\icons\app_icon.png`.

## Step 3: Build Standalone Executable (`PersonalAIWorkspace.exe`)

```bat
backend\.venv\Scripts\pyinstaller.exe --noconfirm --clean packaging\windows\personal_ai_workspace.spec
```

Output: `dist\PersonalAIWorkspace.exe`

This executable bundles Python, FastAPI, SQLAlchemy, Alembic migrations, the compiled React UI, and the desktop launcher into one file. User data persists under `%LOCALAPPDATA%\PersonalAIWorkspace\storage\`.

## Step 4: Build Windows Installer (`PersonalAIWorkspace-Setup-1.0.0.exe`)

With Inno Setup 6 installed:

```bat
iscc packaging\windows\installer.iss
```

Output: `dist\installer\PersonalAIWorkspace-Setup-1.0.0.exe`

Includes:
- Windows 10 & 11 x64 support
- Custom application icon
- Desktop shortcut & Start Menu group
- Clean Windows Uninstaller (preserving user data in `%LOCALAPPDATA%`)
