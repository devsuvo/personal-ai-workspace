from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.database.session import create_db_engine, get_db
from app.main import app
from app.models import Base


@pytest.fixture()
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[dict[str, object], None, None]:
    """Provide an isolated temporary SQLite database, storage directory, and FastAPI TestClient."""
    storage_dir = tmp_path / "storage"
    test_settings = Settings(
        storage_dir=str(storage_dir),
        database_filename="test_personal_ai_workspace.db",
        database_url="",
        encryption_master_key="",
    )
    test_settings.ensure_storage_directories()

    test_engine = create_db_engine(test_settings.effective_database_url)
    Base.metadata.create_all(bind=test_engine)

    # Record current head revision in alembic_version for migration status checks
    with test_engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('0006_productivity_prompts_analytics')"
            )
        )

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    def _override_get_settings() -> Settings:
        return test_settings

    def _override_get_db() -> Generator[Session, None, None]:
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr("app.core.config.get_settings", _override_get_settings)
    monkeypatch.setattr("app.core.security.get_settings", _override_get_settings)
    app.dependency_overrides[get_settings] = _override_get_settings
    app.dependency_overrides[get_db] = _override_get_db

    try:
        with TestClient(app) as client:
            yield {
                "client": client,
                "settings": test_settings,
                "engine": test_engine,
                "session_factory": TestSessionLocal,
            }
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()


@pytest.fixture()
def client(isolated_env: dict[str, object]) -> TestClient:
    return isolated_env["client"]  # type: ignore[return-value]


@pytest.fixture()
def db_session(isolated_env: dict[str, object]) -> Generator[Session, None, None]:
    factory = isolated_env["session_factory"]
    session = factory()  # type: ignore[operator]
    try:
        yield session
    finally:
        session.close()
