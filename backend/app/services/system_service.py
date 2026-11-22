from datetime import datetime, timezone
import platform
import time

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import get_encryption_service
from app.database.session import (
    check_database_connection,
    get_migration_status,
    get_sqlite_file_path,
)
from app.models.provider import Provider
from app.providers.registry import list_planned_providers
from app.schemas.system import (
    ComponentCheck,
    DatabaseStatusResponse,
    HealthChecks,
    HealthResponse,
    MigrationStatus,
    ProviderSummary,
    RuntimeInfo,
    SecurityStatusResponse,
    StorageInfo,
    SystemInfoResponse,
)

APP_STARTED_AT = time.monotonic()


def _check_storage(settings: Settings) -> ComponentCheck:
    required_dirs = (
        settings.storage_root_path,
        settings.database_dir_path,
        settings.uploads_dir_path,
        settings.exports_dir_path,
        settings.backups_dir_path,
        settings.secrets_dir_path,
    )
    missing = [
        settings.relative_storage_label(p)
        for p in required_dirs
        if not p.exists() or not p.is_dir()
    ]
    if missing:
        return ComponentCheck(
            status="error",
            detail=f"Missing storage directories: {', '.join(missing)}",
        )
    return ComponentCheck(status="ok", detail="Local storage directories ready")


def _count_configured_providers(db: Session | None) -> tuple[int, set[str]]:
    if db is None:
        return 0, set()
    try:
        rows = db.execute(
            select(Provider.provider_key).where(Provider.enabled.is_(True))
        ).scalars().all()
        return len(rows), set(rows)
    except Exception:
        return 0, set()


def get_health_status(
    settings: Settings,
    db: Session | None = None,
    db_engine: Engine | None = None,
) -> HealthResponse:
    db_ok, db_error = check_database_connection(db_engine)
    db_check = ComponentCheck(
        status="ok" if db_ok else "error",
        detail="SQLite connection active" if db_ok else db_error,
    )
    storage_check = _check_storage(settings)

    overall_ok = db_check.status == "ok" and storage_check.status == "ok"
    configured_count, _ = _count_configured_providers(db)

    return HealthResponse(
        status="ok" if overall_ok else "degraded",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=round(time.monotonic() - APP_STARTED_AT, 2),
        configured_providers=configured_count,
        checks=HealthChecks(
            database=db_check,
            storage=storage_check,
        ),
    )


def get_system_info(
    settings: Settings,
    db: Session | None = None,
    db_engine: Engine | None = None,
) -> SystemInfoResponse:
    db_ok, _ = check_database_connection(db_engine)
    configured_count, configured_keys = _count_configured_providers(db)
    planned = list_planned_providers()
    provider_summaries = [
        ProviderSummary(
            id=p.id,
            name=p.name,
            description=p.description,
            requires_api_key=p.requires_api_key,
            is_local=p.is_local,
            configured=p.id in configured_keys,
            implemented=p.implemented,
        )
        for p in planned
    ]

    return SystemInfoResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        phase="v1.0.0 — Production Release",
        api_prefix=settings.api_v1_prefix,
        local_only=True,
        configured_providers_count=configured_count,
        planned_providers_count=len(provider_summaries),
        runtime=RuntimeInfo(
            os=platform.system(),
            os_release=platform.release(),
            machine=platform.machine(),
            python_version=platform.python_version(),
        ),
        storage=StorageInfo(
            storage_dir=settings.relative_storage_label(settings.storage_root_path),
            database_path=settings.relative_storage_label(settings.sqlite_db_path),
            uploads_dir=settings.relative_storage_label(settings.uploads_dir_path),
            exports_dir=settings.relative_storage_label(settings.exports_dir_path),
            backups_dir=settings.relative_storage_label(settings.backups_dir_path),
            database_connected=db_ok,
        ),
        planned_providers=provider_summaries,
    )


def get_database_status(
    settings: Settings,
    db_engine: Engine | None = None,
) -> DatabaseStatusResponse:
    db_ok, _ = check_database_connection(db_engine)
    migration = get_migration_status(db_engine)
    db_file = get_sqlite_file_path(db_engine) or settings.sqlite_db_path
    size_bytes = db_file.stat().st_size if db_file.exists() else 0

    return DatabaseStatusResponse(
        connected=db_ok,
        database_type="SQLite",
        database_size_bytes=size_bytes,
        relative_location=settings.relative_storage_label(db_file),
        table_count=int(migration["table_count"]),
        migration_status=MigrationStatus(
            current_revision=migration["current_revision"],
            head_revision=migration["head_revision"],
            is_up_to_date=bool(migration["is_up_to_date"]),
        ),
    )


def get_security_status(settings: Settings) -> SecurityStatusResponse:
    encryption = get_encryption_service()
    status_dict = encryption.get_status(settings)
    return SecurityStatusResponse(**status_dict)
