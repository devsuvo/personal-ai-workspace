from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ComponentCheck(BaseModel):
    status: Literal["ok", "error"]
    detail: str | None = None


class HealthChecks(BaseModel):
    database: ComponentCheck
    storage: ComponentCheck


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app_name: str
    version: str
    environment: str
    timestamp: datetime
    uptime_seconds: float
    configured_providers: int
    checks: HealthChecks


class ProviderSummary(BaseModel):
    id: str
    name: str
    description: str
    requires_api_key: bool
    is_local: bool
    configured: bool
    implemented: bool


class StorageInfo(BaseModel):
    storage_dir: str
    database_path: str
    uploads_dir: str
    exports_dir: str
    backups_dir: str
    database_connected: bool


class RuntimeInfo(BaseModel):
    os: str
    os_release: str
    machine: str
    python_version: str


class SystemInfoResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    phase: str
    api_prefix: str
    local_only: bool
    configured_providers_count: int
    planned_providers_count: int
    runtime: RuntimeInfo
    storage: StorageInfo
    planned_providers: list[ProviderSummary]


class MigrationStatus(BaseModel):
    current_revision: str | None
    head_revision: str | None
    is_up_to_date: bool


class DatabaseStatusResponse(BaseModel):
    connected: bool
    database_type: str
    database_size_bytes: int
    relative_location: str
    table_count: int
    migration_status: MigrationStatus


class SecurityStatusResponse(BaseModel):
    encryption_algorithm: str
    master_key_initialized: bool
    key_source: str
    key_storage_location: str
    secrets_stored_outside_database: bool
    credential_management_status: str
    backup_guidance: str
