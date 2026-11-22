from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve project root reliably across Windows and macOS:
# .../backend/app/core/config.py -> parents[3] is project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Centralized environment-based application settings."""

    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(default="Personal AI Workspace")
    app_version: str = Field(default="1.0.0")
    environment: str = Field(default="production")
    api_v1_prefix: str = Field(default="/api/v1")

    backend_host: str = Field(default="127.0.0.1")
    backend_port: int = Field(default=8000, ge=1, le=65535)

    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173"
    )

    storage_dir: str = Field(default="storage")
    database_filename: str = Field(default="personal_ai_workspace.db")
    database_url: str = Field(default="")
    encryption_master_key: str = Field(default="")
    log_level: str = Field(default="INFO")

    @computed_field
    @property
    def cors_origin_list(self) -> list[str]:
        origins = [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]
        for self_origin in (
            f"http://127.0.0.1:{self.backend_port}",
            f"http://localhost:{self.backend_port}",
        ):
            if self_origin not in origins:
                origins.append(self_origin)
        return origins

    @computed_field
    @property
    def storage_root_path(self) -> Path:
        configured = Path(self.storage_dir)
        if configured.is_absolute():
            return configured.resolve()
        return (PROJECT_ROOT / configured).resolve()

    @computed_field
    @property
    def database_dir_path(self) -> Path:
        return self.storage_root_path / "database"

    @computed_field
    @property
    def uploads_dir_path(self) -> Path:
        return self.storage_root_path / "uploads"

    @computed_field
    @property
    def exports_dir_path(self) -> Path:
        return self.storage_root_path / "exports"

    @computed_field
    @property
    def backups_dir_path(self) -> Path:
        return self.storage_root_path / "backups"

    @computed_field
    @property
    def secrets_dir_path(self) -> Path:
        return self.storage_root_path / "secrets"

    @computed_field
    @property
    def master_key_path(self) -> Path:
        return self.secrets_dir_path / "master.key"

    @computed_field
    @property
    def sqlite_db_path(self) -> Path:
        return self.database_dir_path / self.database_filename

    @computed_field
    @property
    def effective_database_url(self) -> str:
        if self.database_url.strip():
            return self.database_url.strip()
        return f"sqlite:///{self.sqlite_db_path.as_posix()}"

    def relative_storage_label(self, path: Path) -> str:
        """Return a safe, non-private relative display path for API responses."""
        try:
            return path.resolve().relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            try:
                rel = path.resolve().relative_to(self.storage_root_path).as_posix()
                return f"storage/{rel}" if rel != "." else "storage"
            except ValueError:
                return path.name

    def ensure_storage_directories(self) -> None:
        """Create local storage directories if they do not exist."""
        self.storage_root_path.mkdir(parents=True, exist_ok=True)
        self.database_dir_path.mkdir(parents=True, exist_ok=True)
        self.uploads_dir_path.mkdir(parents=True, exist_ok=True)
        self.exports_dir_path.mkdir(parents=True, exist_ok=True)
        self.backups_dir_path.mkdir(parents=True, exist_ok=True)
        self.secrets_dir_path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
