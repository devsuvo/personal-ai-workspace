# Changelog

All notable changes to **Personal AI Workspace** are documented here.

## [1.0.0] — Production Release (Phase 7)
- Added OS keyring integration (`keyring`) for Windows Credential Manager & macOS Keychain support alongside Fernet encryption.
- Added production static frontend serving from FastAPI and standalone `desktop_launcher.py` with automatic Alembic migrations and per-user persistent storage.
- Added **Clear Local Data** (`POST /api/v1/system/backups/clear-data`) with explicit confirmation and automatic `pre_clear_*.db` safety snapshots.
- Optimized Vite production build with vendor code splitting (`react-vendor`, `markdown-vendor`, `syntax-vendor`, `icons-vendor`).
- Generated multi-resolution Windows `.ico` / `.png` app icons and added PyInstaller (`PersonalAIWorkspace.exe`), Inno Setup (`installer.iss`), and macOS (`build_macos.sh`) packaging configurations.
- Added complete production documentation (`INSTALLATION.md`, `WINDOWS_BUILD.md`, `MACOS_BUILD.md`, `API_SETUP.md`, `BACKUP_RESTORE.md`, `CHANGELOG.md`).

## [0.6.0] — Phase 6: Advanced Tools, Analytics & Productivity
- Added **AI Tools** (9 built-in tools: Summarizer, Rewriter, Grammar Corrector, Translator, Code Explainer, Code Generator, Content Generator, Email Writer, Custom Prompt Runner).
- Added **Prompt Library** with categories, favorites, search, and one-click Use in Chat.
- Added interactive **Usage Analytics** dashboard with daily/monthly charts, top models table, and optional user-configured model pricing.
- Added conversation pinning, Markdown/TXT export, clear conversation, model/date filtering, and keyboard shortcuts (`Ctrl+Shift+N`).

## [0.5.0] — Phase 5: Projects, File Management & Artifacts
- Added **Projects** with custom instructions, archiving, safe deletion, and conversation assignment.
- Added local **File Management** and text extraction for PDF (`PyMuPDF` with scanned-PDF OCR detection), DOCX (`python-docx`), XLSX (`openpyxl`), and text/code/image files.
- Added **Chat With Files** context injection and **Artifacts** workspace with sandboxed HTML preview (`sandbox=""`) and Save as Artifact from chat.

## [0.4.0] — Phase 4: Multi-Provider AI Chat & Streaming
- Implemented unified streaming & non-streaming chat across Anthropic, Google Gemini, OpenAI, OpenAI-compatible providers, and Ollama.
- Added SSE streaming (`POST /api/v1/chat/stream`), Stop generation, Markdown + Prism code highlighting + KaTeX math, Copy, Regenerate, Edit & Resend, and context window truncation.

## [0.3.0] — Phase 3: Dynamic AI Provider & API Key Management
- Implemented 10-provider catalog, encrypted multi-credential storage with masked fingerprints, lightweight connection testing, model discovery, and manual model registration.

## [0.2.0] — Phase 2: Database, Settings & Local Security
- Implemented SQLAlchemy 2.0 core schema, Alembic migrations, validated Settings API + 6-section Settings UI, Fernet encryption service, and online SQLite backup/restore.

## [0.1.0] — Phase 1: Project Foundation
- Initialized local-first FastAPI + SQLite + React + TypeScript + Tailwind workspace shell with dark/light themes and Windows startup scripts.
