from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.schemas.backup import (
    BackupCreateResponse,
    BackupListResponse,
    BackupRestoreRequest,
    BackupRestoreResponse,
    BackupValidationResponse,
    ClearLocalDataRequest,
    ClearLocalDataResponse,
)
from app.services import backup_service

router = APIRouter(prefix="/system/backups", tags=["Backups"])


@router.post(
    "/clear-data",
    response_model=ClearLocalDataResponse,
    summary="Safely clear selected local data after creating an automatic backup",
)
def clear_workspace_data(
    payload: ClearLocalDataRequest,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> ClearLocalDataResponse:
    return backup_service.clear_local_data(
        db,
        settings,
        scope=payload.scope,
        confirm=payload.confirm,
        db_engine=db.get_bind(),
    )


@router.get(
    "",
    response_model=BackupListResponse,
    summary="List local SQLite database backups",
)
def get_backups(
    settings: Settings = Depends(get_settings),
) -> BackupListResponse:
    return BackupListResponse(backups=backup_service.list_backups(settings))


@router.post(
    "",
    response_model=BackupCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a safe local SQLite backup",
)
def create_database_backup(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> BackupCreateResponse:
    return backup_service.create_backup(settings, db_engine=db.get_bind())


@router.post(
    "/{filename}/validate",
    response_model=BackupValidationResponse,
    summary="Validate SQLite integrity of a backup file",
)
def validate_database_backup(
    filename: str,
    settings: Settings = Depends(get_settings),
) -> BackupValidationResponse:
    return backup_service.validate_backup(settings, filename)


@router.post(
    "/{filename}/restore",
    response_model=BackupRestoreResponse,
    summary="Restore the local SQLite database from a validated backup",
)
def restore_database_backup(
    filename: str,
    payload: BackupRestoreRequest,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> BackupRestoreResponse:
    return backup_service.restore_backup(
        settings,
        filename=filename,
        confirm=payload.confirm,
        db_engine=db.get_bind(),
    )
