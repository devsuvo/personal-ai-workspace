# Backup & Restore Guide

All workspace data is stored locally on your machine in SQLite (`storage/database/personal_ai_workspace.db` in source mode, or under `%LOCALAPPDATA%\PersonalAIWorkspace\storage\` on Windows / `~/Library/Application Support/PersonalAIWorkspace/storage/` on macOS in packaged mode).

## Creating a Backup

1. Open **Settings → Data Backup**.
2. Click **Create Backup**.
3. The backend uses SQLite's online `Connection.backup()` API to create a consistent snapshot under `storage/backups/backup_YYYYMMDD_HHMMSS_*.db`.

## Validating a Backup

Click **Validate** next to any backup to verify:
- Valid SQLite 3 header
- `PRAGMA integrity_check` returns `ok`
- Valid Alembic schema revision

## Restoring a Backup

1. Click **Restore** next to a validated backup.
2. Confirm the overwrite prompt.
3. The backend automatically saves a `pre_restore_*.db` snapshot of your current database before restoring, disposes active SQLite connections cleanly, restores the selected backup, and verifies reconnection.

## Backing Up Your Encryption Master Key

- Your Fernet master key is stored **outside SQLite** at `storage/secrets/master.key` (with OS keyring support via `keyring` on Windows Credential Manager / macOS Keychain).
- Keep an offline copy of `master.key` in a password manager or encrypted USB drive.
- Never commit `master.key` to Git. If lost, encrypted API keys cannot be decrypted and must be re-entered.

## Clearing Local Data Safely

Under **Settings → Data Backup → Clear Local Data**, you can clear Conversations, Usage Logs, or All Workspace Data. Every clear action automatically creates a `pre_clear_*.db` backup first and preserves your configured providers and master key.
