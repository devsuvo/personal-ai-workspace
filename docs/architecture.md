# Architecture Overview — Phase 1 Foundation

## Local-First Design Principles

Personal AI Workspace is designed to run completely independently on a single computer (Windows or macOS) with zero cloud dependency:

- **Backend**: Python 3.12+ + FastAPI bound to `127.0.0.1:8000`.
- **Frontend**: React + TypeScript + Vite + Tailwind CSS served locally on port `5173`.
- **Database**: SQLite stored locally at `storage/database/workspace.db`, managed via SQLAlchemy 2.0 and Alembic migrations.
- **File Storage**: Local filesystem directories under `storage/uploads/` and `storage/exports/`.
- **Zero Hardcoded Secrets**: No API keys are embedded or required for installation or startup.

## Backend Module Boundaries

- `app/core/`: Environment configuration (`pydantic-settings`), logging setup, and consistent structured error responses.
- `app/database/`: SQLAlchemy declarative `Base`, `TimestampMixin`, SQLite pragma setup (`foreign_keys=ON`, `journal_mode=WAL`), and session management.
- `app/models/`: ORM model registry for future phases (Conversations, Messages, Projects, Providers, API Credentials, Models, Attachments, Usage Logs, App Settings).
- `app/providers/`: Abstract provider interface and static registry of the 9 planned AI providers.
- `app/schemas/`: Pydantic request/response contracts.
- `app/services/`: Business logic decoupled from HTTP routing.
- `app/api/v1/`: Versioned REST endpoints (`/api/v1/health`, `/api/v1/system/info`).

## Frontend Module Boundaries

- `src/layouts/`: Persistent `WorkspaceLayout` shell.
- `src/components/`: Reusable layout (`Sidebar`, `TopNav`), chat (`MessageComposer`), and shared UI primitives (`StatusBadge`, `EmptyStateCard`).
- `src/pages/`: Clean route views (`Chat`, `Projects`, `Artifacts`, `AI Providers`, `Usage`, `Settings`).
- `src/services/`: Typed REST API client (`apiClient.ts`, `systemService.ts`).
- `src/hooks/`: Theme persistence (`useTheme.ts`) and live backend status (`useSystemStatus.ts`).
- `src/types/`: Strict TypeScript interfaces matching backend Pydantic schemas.
