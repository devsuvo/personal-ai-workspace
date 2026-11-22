# Personal AI Workspace (v1.0.0)

A complete, locally hosted, multi-provider AI desktop workspace built with **Python 3.12**, **FastAPI**, **SQLAlchemy 2.0**, **SQLite**, **Alembic**, **React**, **TypeScript**, and **Tailwind CSS**.

Designed to run independently on **Windows** and **macOS** with zero cloud dependency—each computer maintains its own local SQLite database, encrypted API credentials, uploaded files, projects, prompts, and chat history.

---

## Core Capabilities

- **Multi-Provider AI Chat & Real-Time Streaming**: Unified SSE streaming chat across **10 providers** (Anthropic Claude, Google Gemini Developer API, OpenAI, DeepSeek, xAI Grok, Mistral AI, Groq, OpenRouter, Ollama local models, and Custom OpenAI-Compatible endpoints).
- **Rich Chat Experience**: Markdown, GFM tables, Prism syntax-highlighted code blocks, KaTeX math, Stop generation, Copy, Regenerate, Edit & Resend, Pin conversations, Search, Clear, and Export to Markdown/TXT.
- **Encrypted Local Credential Vault**: Fernet (`AES-128-CBC + HMAC-SHA256`) encryption with master key stored outside SQLite + OS Keyring support (`keyring`), masked key fingerprints (`sk-****abcd`), and log redaction.
- **Projects, File Reading & Artifacts**: Dedicated project workspaces with layered AI instructions, local file uploads with PDF/DOCX/XLSX/code text extraction (plus honest OCR detection for scanned PDFs), Chat With Files, and standalone Artifacts with sandboxed HTML previews.
- **AI Tools, Prompt Library & Analytics**: 9 built-in AI productivity tools, categorized favorite Prompt Library, and an interactive local Usage Analytics dashboard with daily/monthly charts and configurable model pricing.
- **Safe Backup, Restore & Data Controls**: Online SQLite backups, `PRAGMA integrity_check` validation, confirmed restore with automatic safety snapshots, and safe Clear Local Data.

---

## Quick Start (Windows)

```bat
install.bat
start.bat
```

Or launch the standalone packaged executable: `dist\PersonalAIWorkspace.exe`

## Documentation

- [INSTALLATION.md](INSTALLATION.md) — Windows & macOS installation, updates, and troubleshooting
- [API_SETUP.md](API_SETUP.md) — Configuring the 10 AI providers, API keys, and Ollama
- [BACKUP_RESTORE.md](BACKUP_RESTORE.md) — Backing up SQLite, master key safety, and restoring data
- [WINDOWS_BUILD.md](WINDOWS_BUILD.md) — Building `PersonalAIWorkspace.exe` and Inno Setup installer
- [MACOS_BUILD.md](MACOS_BUILD.md) — Building `PersonalAIWorkspace.app` and `.dmg` on macOS
- [CHANGELOG.md](CHANGELOG.md) — Version history and release notes
- [docs/database.md](docs/database.md) & [docs/providers.md](docs/providers.md) — Architecture references
