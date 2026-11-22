from datetime import datetime

from pydantic import BaseModel, Field


class BackupInfo(BaseModel):
    filename: str
    size_bytes: int
    created_at: datetime
    relative_location: str


class BackupListResponse(BaseModel):
    backups: list[BackupInfo]


class BackupCreateResponse(BaseModel):
    backup: BackupInfo
    message: str


class BackupValidationResponse(BaseModel):
    filename: str
    is_valid: bool
    integrity_check: str
    schema_revision: str | None = None
    detail: str


class BackupRestoreRequest(BaseModel):
    confirm: bool = Field(
        default=False,
        description="Must be explicitly set to true to overwrite the active local database.",
    )


class BackupRestoreResponse(BaseModel):
    restored_from: str
    pre_restore_backup: str
    database_connected: bool
    message: str


class ClearLocalDataRequest(BaseModel):
    confirm: bool = Field(
        default=False,
        description="Must be explicitly true to clear local workspace data.",
    )
    scope: str = Field(
        default="conversations",
        pattern="^(conversations|usage_logs|all_workspace_data)$",
    )


class ClearLocalDataResponse(BaseModel):
    scope: str
    pre_clear_backup: str
    message: str
