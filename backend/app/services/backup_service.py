from datetime import datetime, timezone
import logging
from pathlib import Path
import sqlite3
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import PathValidationError, sanitize_filename, validate_safe_path
from app.database.session import (
    check_database_connection,
    dispose_engine,
    get_sqlite_file_path,
)
from app.models import (
    Artifact,
    Attachment,
    Conversation,
    Message,
    Project,
    PromptTemplate,
    UsageLog,
)
from app.schemas.backup import (
    BackupCreateResponse,
    BackupInfo,
    BackupRestoreResponse,
    BackupValidationResponse,
    ClearLocalDataResponse,
)

logger = logging.getLogger("workspace.backup")

SQLITE_HEADER_PREFIX = b"SQLite format 3\x00"


def _resolve_active_db_path(settings: Settings, db_engine: Engine | None = None) -> Path:
    db_path = get_sqlite_file_path(db_engine) or settings.sqlite_db_path
    if not db_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Active SQLite database file does not exist.",
        )
    return db_path


def _resolve_backup_file(settings: Settings, filename: str) -> Path:
    try:
        clean_name = sanitize_filename(filename)
        if not clean_name.endswith(".db"):
            raise PathValidationError("Backup filename must end with .db.")
        return validate_safe_path(settings.backups_dir_path, clean_name)
    except PathValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


def _to_backup_info(settings: Settings, path: Path) -> BackupInfo:
    stat = path.stat()
    return BackupInfo(
        filename=path.name,
        size_bytes=stat.st_size,
        created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        relative_location=settings.relative_storage_label(path),
    )


def _sqlite_hot_backup(source_path: Path, destination_path: Path) -> None:
    """Safely copy an active SQLite database using SQLite's online backup API."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    src_conn = sqlite3.connect(str(source_path))
    dst_conn = sqlite3.connect(str(destination_path))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


def create_backup(
    settings: Settings,
    prefix: str = "backup",
    db_engine: Engine | None = None,
) -> BackupCreateResponse:
    settings.ensure_storage_directories()
    source_db = _resolve_active_db_path(settings, db_engine)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    short_id = uuid4().hex[:6]
    filename = f"{prefix}_{timestamp}_{short_id}.db"
    destination = validate_safe_path(settings.backups_dir_path, filename)

    try:
        _sqlite_hot_backup(source_db, destination)
    except Exception as exc:
        logger.exception("Failed to create SQLite backup: %s", exc)
        if destination.exists():
            destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create local database backup.",
        ) from exc

    info = _to_backup_info(settings, destination)
    logger.info("Created SQLite backup %s (%d bytes)", info.filename, info.size_bytes)
    return BackupCreateResponse(
        backup=info,
        message=f"Backup '{info.filename}' created successfully.",
    )


def list_backups(settings: Settings) -> list[BackupInfo]:
    settings.ensure_storage_directories()
    files = sorted(
        settings.backups_dir_path.glob("*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [_to_backup_info(settings, f) for f in files]


def validate_backup(
    settings: Settings,
    filename: str,
) -> BackupValidationResponse:
    backup_path = _resolve_backup_file(settings, filename)
    if not backup_path.exists() or not backup_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup file '{filename}' was not found.",
        )

    # Check SQLite magic header first
    try:
        with open(backup_path, "rb") as fh:
            header = fh.read(16)
    except OSError as exc:
        return BackupValidationResponse(
            filename=backup_path.name,
            is_valid=False,
            integrity_check="unreadable",
            detail=f"Could not read backup file: {exc}",
        )

    if header != SQLITE_HEADER_PREFIX:
        return BackupValidationResponse(
            filename=backup_path.name,
            is_valid=False,
            integrity_check="invalid_header",
            detail="File is not a valid SQLite 3 database.",
        )

    try:
        conn = sqlite3.connect(f"file:{backup_path.as_posix()}?mode=ro", uri=True)
        try:
            integrity_row = conn.execute("PRAGMA integrity_check;").fetchone()
            integrity = str(integrity_row[0]) if integrity_row else "unknown"
            if integrity.lower() != "ok":
                return BackupValidationResponse(
                    filename=backup_path.name,
                    is_valid=False,
                    integrity_check=integrity,
                    detail=f"SQLite integrity check failed: {integrity}",
                )

            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table';"
                ).fetchall()
            }
            revision: str | None = None
            if "alembic_version" in tables:
                rev_row = conn.execute(
                    "SELECT version_num FROM alembic_version LIMIT 1;"
                ).fetchone()
                if rev_row:
                    revision = str(rev_row[0])

            return BackupValidationResponse(
                filename=backup_path.name,
                is_valid=True,
                integrity_check="ok",
                schema_revision=revision,
                detail="Backup passed SQLite integrity and schema verification.",
            )
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        return BackupValidationResponse(
            filename=backup_path.name,
            is_valid=False,
            integrity_check="corrupt",
            detail=f"Backup database could not be verified: {exc}",
        )


def restore_backup(
    settings: Settings,
    filename: str,
    confirm: bool,
    db_engine: Engine | None = None,
) -> BackupRestoreResponse:
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restore requires explicit confirmation (confirm=true) before overwriting the active database.",
        )

    validation = validate_backup(settings, filename)
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot restore invalid backup '{filename}': {validation.detail}",
        )

    backup_path = _resolve_backup_file(settings, filename)
    active_db = _resolve_active_db_path(settings, db_engine)

    # Always create a safety backup before overwriting the live database
    safety_backup = create_backup(settings, prefix="pre_restore", db_engine=db_engine)

    # Release SQLAlchemy connections so SQLite restore completes cleanly
    if db_engine is not None:
        db_engine.dispose()
    else:
        dispose_engine()

    try:
        _sqlite_hot_backup(backup_path, active_db)
    except Exception as exc:
        logger.exception("Database restore failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore database from backup.",
        ) from exc

    connected, err = check_database_connection(db_engine)
    if not connected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database restored but reconnection failed: {err}",
        )

    logger.info("Restored SQLite database from %s", backup_path.name)
    return BackupRestoreResponse(
        restored_from=backup_path.name,
        pre_restore_backup=safety_backup.backup.filename,
        database_connected=True,
        message=f"Database restored from '{backup_path.name}'. A safety snapshot was saved as '{safety_backup.backup.filename}'.",
    )


def clear_local_data(
    db: Session,
    settings: Settings,
    scope: str,
    confirm: bool,
    db_engine: Engine | None = None,
) -> ClearLocalDataResponse:
    """Safely clear selected local data after creating an automatic pre-clear backup."""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clearing local data requires explicit confirmation (confirm=true).",
        )

    safety_backup = create_backup(settings, prefix="pre_clear", db_engine=db_engine)

    if scope == "conversations":
        db.execute(delete(Message))
        db.execute(delete(Conversation))
    elif scope == "usage_logs":
        db.execute(delete(UsageLog))
    elif scope == "all_workspace_data":
        db.execute(delete(UsageLog))
        db.execute(delete(Artifact))
        db.execute(delete(Attachment))
        db.execute(delete(Message))
        db.execute(delete(Conversation))
        db.execute(delete(Project))
        db.execute(delete(PromptTemplate))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported clear scope '{scope}'.",
        )

    db.commit()
    logger.info("Cleared local data (scope=%s); safety backup=%s", scope, safety_backup.backup.filename)
    return ClearLocalDataResponse(
        scope=scope,
        pre_clear_backup=safety_backup.backup.filename,
        message=(
            f"Cleared '{scope}' successfully. A safety backup was saved as "
            f"'{safety_backup.backup.filename}'."
        ),
    )
