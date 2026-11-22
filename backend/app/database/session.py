from collections.abc import Generator
import logging
from pathlib import Path
from typing import Any

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BACKEND_ROOT, get_settings

logger = logging.getLogger("workspace.database")


def _configure_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    """Enable foreign keys and WAL mode for reliable local SQLite operation."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.close()


def create_db_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    settings.ensure_storage_directories()
    url = database_url or settings.effective_database_url

    connect_args: dict[str, Any] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    db_engine = create_engine(
        url,
        connect_args=connect_args,
        future=True,
        pool_pre_ping=True,
    )

    if url.startswith("sqlite"):
        event.listen(db_engine, "connect", _configure_sqlite_pragmas)

    return db_engine


engine: Engine = create_db_engine()
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped SQLAlchemy session with safe rollback."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def dispose_engine() -> None:
    """Release all pooled database connections (used before safe restore)."""
    engine.dispose()


def check_database_connection(db_engine: Engine | None = None) -> tuple[bool, str | None]:
    """Verify the SQLite database is reachable and responsive."""
    target_engine = db_engine or engine
    try:
        with target_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return False, str(exc)


def get_alembic_head_revision() -> str | None:
    """Return the latest Alembic migration revision defined in backend/alembic."""
    ini_path = BACKEND_ROOT / "alembic.ini"
    if not ini_path.exists():
        return None
    try:
        alembic_cfg = AlembicConfig(str(ini_path))
        alembic_cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
        script = ScriptDirectory.from_config(alembic_cfg)
        return script.get_current_head()
    except Exception as exc:
        logger.warning("Could not read Alembic head revision: %s", exc)
        return None


def get_migration_status(db_engine: Engine | None = None) -> dict[str, Any]:
    """Inspect current applied revision vs Alembic head revision."""
    target_engine = db_engine or engine
    head_revision = get_alembic_head_revision()
    current_revision: str | None = None
    table_count = 0

    try:
        inspector = inspect(target_engine)
        tables = inspector.get_table_names()
        table_count = len([t for t in tables if t != "alembic_version"])
        if "alembic_version" in tables:
            with target_engine.connect() as conn:
                row = conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                ).fetchone()
                if row:
                    current_revision = str(row[0])
    except Exception as exc:
        logger.warning("Could not inspect database migration status: %s", exc)

    return {
        "current_revision": current_revision,
        "head_revision": head_revision,
        "is_up_to_date": (
            current_revision is not None
            and head_revision is not None
            and current_revision == head_revision
        ),
        "table_count": table_count,
    }


def get_sqlite_file_path(db_engine: Engine | None = None) -> Path | None:
    """Resolve the underlying SQLite file path for a given engine."""
    target_engine = db_engine or engine
    db_name = target_engine.url.database
    if not db_name or db_name == ":memory:":
        return None
    return Path(db_name).resolve()


def init_database() -> None:
    """Ensure local storage and SQLite database file are initialized."""
    settings = get_settings()
    settings.ensure_storage_directories()
    ok, error = check_database_connection()
    if not ok:
        raise RuntimeError(f"Failed to initialize SQLite database: {error}")
    logger.info("SQLite database ready (%s)", settings.relative_storage_label(settings.sqlite_db_path))
