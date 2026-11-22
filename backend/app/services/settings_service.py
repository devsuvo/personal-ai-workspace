from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting
from app.providers.registry import list_planned_providers
from app.schemas.settings import SettingDeleteResponse, SettingItem

FORBIDDEN_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
    "master_key",
    "private_key",
    "credential",
)


@dataclass(frozen=True)
class SettingDefinition:
    key: str
    category: str
    description: str
    default_value: Any
    value_type: str  # "str" | "nullable_str" | "bool" | "int" | "enum"
    allowed_values: tuple[str, ...] = ()
    min_value: int | None = None
    max_value: int | None = None
    max_length: int | None = None


SETTING_DEFINITIONS: tuple[SettingDefinition, ...] = (
    SettingDefinition(
        key="app_name",
        category="general",
        description="Display name for this local AI workspace.",
        default_value="Personal AI Workspace",
        value_type="str",
        max_length=80,
    ),
    SettingDefinition(
        key="theme",
        category="appearance",
        description="Interface color theme (light, dark, or system).",
        default_value="light",
        value_type="enum",
        allowed_values=("light", "dark", "system"),
    ),
    SettingDefinition(
        key="sidebar_collapsed",
        category="appearance",
        description="Whether the left navigation sidebar starts collapsed.",
        default_value=False,
        value_type="bool",
    ),
    SettingDefinition(
        key="default_provider",
        category="general",
        description="Default AI provider ID or key for new conversations.",
        default_value=None,
        value_type="nullable_str",
        max_length=64,
    ),
    SettingDefinition(
        key="default_model",
        category="general",
        description="Default AI model identifier for new conversations.",
        default_value=None,
        value_type="nullable_str",
        max_length=160,
    ),
    SettingDefinition(
        key="chat_send_on_enter",
        category="chat",
        description="Send messages when pressing Enter (Shift+Enter inserts a newline).",
        default_value=True,
        value_type="bool",
    ),
    SettingDefinition(
        key="chat_stream_responses",
        category="chat",
        description="Stream AI replies incrementally when supported by the provider.",
        default_value=True,
        value_type="bool",
    ),
    SettingDefinition(
        key="chat_show_token_usage",
        category="chat",
        description="Display token usage summaries alongside completed responses.",
        default_value=True,
        value_type="bool",
    ),
    SettingDefinition(
        key="chat_default_system_prompt",
        category="chat",
        description="Optional default system instruction applied to new conversations.",
        default_value="",
        value_type="str",
        max_length=4000,
    ),
    SettingDefinition(
        key="max_upload_size_mb",
        category="storage",
        description="Maximum allowed file upload size in megabytes (1 to 500 MB).",
        default_value=25,
        value_type="int",
        min_value=1,
        max_value=500,
    ),
)

DEFINITIONS_BY_KEY: dict[str, SettingDefinition] = {
    item.key: item for item in SETTING_DEFINITIONS
}


def _assert_not_secret_key(key: str) -> None:
    lowered = key.lower()
    if any(fragment in lowered for fragment in FORBIDDEN_KEY_FRAGMENTS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sensitive credentials or secrets cannot be stored in application settings.",
        )


def _get_definition(key: str) -> SettingDefinition:
    _assert_not_secret_key(key)
    definition = DEFINITIONS_BY_KEY.get(key)
    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown application setting '{key}'.",
        )
    return definition


def _validate_value(definition: SettingDefinition, value: Any) -> Any:
    if definition.value_type == "bool":
        if not isinstance(value, bool):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Setting '{definition.key}' requires a boolean value.",
            )
        return value

    if definition.value_type == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Setting '{definition.key}' requires an integer value.",
            )
        if definition.min_value is not None and value < definition.min_value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Setting '{definition.key}' must be at least {definition.min_value}.",
            )
        if definition.max_value is not None and value > definition.max_value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Setting '{definition.key}' must be at most {definition.max_value}.",
            )
        return value

    if definition.value_type == "enum":
        if not isinstance(value, str) or value not in definition.allowed_values:
            allowed = ", ".join(definition.allowed_values)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Setting '{definition.key}' must be one of: {allowed}.",
            )
        return value

    if definition.value_type == "str":
        if not isinstance(value, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Setting '{definition.key}' requires a string value.",
            )
        cleaned = value.strip() if definition.key == "app_name" else value
        if definition.key == "app_name" and not cleaned:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Application name cannot be empty.",
            )
        if definition.max_length is not None and len(cleaned) > definition.max_length:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Setting '{definition.key}' exceeds maximum length of {definition.max_length}.",
            )
        return cleaned

    if definition.value_type == "nullable_str":
        if value is None or value == "":
            return None
        if not isinstance(value, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Setting '{definition.key}' requires a string or null value.",
            )
        cleaned = value.strip()
        if definition.max_length is not None and len(cleaned) > definition.max_length:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Setting '{definition.key}' exceeds maximum length of {definition.max_length}.",
            )
        return cleaned or None

    return value


def _to_setting_item(
    definition: SettingDefinition, record: AppSetting | None
) -> SettingItem:
    return SettingItem(
        key=definition.key,
        value=record.setting_value if record is not None else definition.default_value,
        default_value=definition.default_value,
        category=definition.category,
        description=definition.description,
        is_custom=record is not None,
        updated_at=record.updated_at if record is not None else None,
    )


def list_settings(db: Session) -> list[SettingItem]:
    rows = db.execute(select(AppSetting)).scalars().all()
    by_key = {row.setting_key: row for row in rows}
    return [_to_setting_item(defn, by_key.get(defn.key)) for defn in SETTING_DEFINITIONS]


def get_setting(db: Session, key: str) -> SettingItem:
    definition = _get_definition(key)
    record = db.execute(
        select(AppSetting).where(AppSetting.setting_key == key)
    ).scalar_one_or_none()
    return _to_setting_item(definition, record)


def upsert_setting(db: Session, key: str, value: Any) -> SettingItem:
    definition = _get_definition(key)
    validated_value = _validate_value(definition, value)

    record = db.execute(
        select(AppSetting).where(AppSetting.setting_key == key)
    ).scalar_one_or_none()

    if record is None:
        record = AppSetting(setting_key=key, setting_value=validated_value)
        db.add(record)
    else:
        record.setting_value = validated_value

    db.commit()
    db.refresh(record)
    return _to_setting_item(definition, record)


def delete_setting(db: Session, key: str) -> SettingDeleteResponse:
    definition = _get_definition(key)
    record = db.execute(
        select(AppSetting).where(AppSetting.setting_key == key)
    ).scalar_one_or_none()

    if record is not None:
        db.delete(record)
        db.commit()

    return SettingDeleteResponse(
        key=definition.key,
        reset_to_default=True,
        default_value=definition.default_value,
    )


def list_supported_provider_keys() -> list[str]:
    return [p.id for p in list_planned_providers()]
