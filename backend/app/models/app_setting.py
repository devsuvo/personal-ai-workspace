from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class AppSetting(TimestampMixin, Base):
    """Non-sensitive application configuration stored locally in SQLite."""

    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    setting_key: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    setting_value: Mapped[Any] = mapped_column(JSON, nullable=True)
