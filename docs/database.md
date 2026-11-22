# Database & Local Security Architecture

## 1. Local SQLite Storage

- **Default Location**: `storage/database/personal_ai_workspace.db` (configurable via `STORAGE_DIR`, `DATABASE_FILENAME`, or `DATABASE_URL`).
- **Engine Configuration**: SQLAlchemy 2.0 with `PRAGMA foreign_keys=ON` and `PRAGMA journal_mode=WAL` enabled on every connection.
- **Migrations**: Managed via Alembic (`backend/alembic/versions/`):
  - `0001_initial_foundation` — baseline version tracking
  - `0002_core_workspace_tables` — `app_settings`, `projects`, `conversations`, `messages`, `attachments`, `usage_logs`
  - `0003_provider_management_tables` — `providers`, `provider_credentials`, `provider_models`

## 2. Core Schema

| Table | Purpose | Key Relationships |
| ----- | ------- | ----------------- |
| `app_settings` | Non-sensitive workspace settings (`setting_key`, JSON `setting_value`) | Unique `setting_key`; blocks secret/credential keys |
| `projects` | Project workspaces (`name`, `description`, `instructions`) | 1:N `conversations`, 1:N `attachments` |
| `conversations` | Chat threads (`title`, `provider_id`, `model_name`, `system_prompt`) | N:1 `projects` (`SET NULL`), 1:N `messages` (`CASCADE`) |
| `messages` | Chat turns (`role`, `content`, JSON `content_blocks`, `tool_calls`, `token_usage`) | N:1 `conversations` (`CASCADE`) |
| `attachments` | Local uploaded file metadata (`original_filename`, `stored_filename`, `mime_type`, `file_size`, `storage_path`) | Optional FKs to `conversations`, `messages`, `projects` |
| `usage_logs` | Token and cost ledger (`provider_name`, `model_name`, `input_tokens`, `output_tokens`, `estimated_cost`, `request_status`) | Optional FKs to `conversations`, `messages` |
| `providers` | Configured AI providers (`provider_key`, `display_name`, `provider_type`, `base_url`, `enabled`, `default_model`, `connection_status`) | 1:N `provider_credentials` (`CASCADE`), 1:N `provider_models` (`CASCADE`) |
| `provider_credentials` | Encrypted API keys (`credential_name`, `encrypted_api_key`, `key_fingerprint`, `is_active`) | N:1 `providers` (`CASCADE`) |
| `provider_models` | Discovered or manually added models (`model_id`, `display_name`, JSON `capabilities`, `is_available`, `is_manual`) | N:1 `providers` (`CASCADE`), unique `(provider_id, model_id)` |

## 3. Encryption & Key Management

- **Algorithm**: Fernet authenticated encryption (AES-128-CBC + HMAC-SHA256) from Python `cryptography`.
- **Master Key Storage**: Stored **outside** SQLite at `storage/secrets/master.key` (or overridden via `ENCRYPTION_MASTER_KEY`). Never committed to Git, never returned to the frontend, and never printed in logs.
- **No Silent Regeneration**: If encrypted credentials exist in SQLite and the master key file is missing, the backend refuses to generate a new key and instructs the user to restore their backed-up `master.key`.
- **Log Redaction**: `SecretRedactingFilter` masks common API key prefixes, Bearer headers, and Fernet ciphertexts in backend logs.

## 4. Safe Backup & Restore

- Backups use SQLite's native online `Connection.backup()` API and are stored in `storage/backups/`.
- Validation checks the SQLite magic header, runs `PRAGMA integrity_check;`, and inspects `alembic_version`.
- Restore requires explicit `confirm: true`, validates the target backup, creates an automatic `pre_restore_*.db` snapshot, disposes SQLAlchemy connections, restores safely, and verifies reconnection.
