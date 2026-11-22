from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SettingItem(BaseModel):
    key: str
    value: Any
    default_value: Any
    category: str
    description: str
    is_custom: bool
    updated_at: datetime | None = None


class SettingsListResponse(BaseModel):
    settings: list[SettingItem]


class SettingUpdateRequest(BaseModel):
    value: Any = Field(..., description="New validated value for the application setting.")


class SettingDeleteResponse(BaseModel):
    key: str
    reset_to_default: bool
    default_value: Any
