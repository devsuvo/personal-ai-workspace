from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.settings import (
    SettingDeleteResponse,
    SettingItem,
    SettingsListResponse,
    SettingUpdateRequest,
)
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get(
    "",
    response_model=SettingsListResponse,
    summary="List all application settings",
)
def list_all_settings(db: Session = Depends(get_db)) -> SettingsListResponse:
    return SettingsListResponse(settings=settings_service.list_settings(db))


@router.get(
    "/{key}",
    response_model=SettingItem,
    summary="Get a single application setting by key",
)
def read_setting(key: str, db: Session = Depends(get_db)) -> SettingItem:
    return settings_service.get_setting(db, key)


@router.put(
    "/{key}",
    response_model=SettingItem,
    summary="Create or update a validated application setting",
)
def update_setting(
    key: str,
    payload: SettingUpdateRequest,
    db: Session = Depends(get_db),
) -> SettingItem:
    return settings_service.upsert_setting(db, key, payload.value)


@router.delete(
    "/{key}",
    response_model=SettingDeleteResponse,
    summary="Reset an application setting to its default value",
)
def remove_setting(
    key: str, db: Session = Depends(get_db)
) -> SettingDeleteResponse:
    return settings_service.delete_setting(db, key)
