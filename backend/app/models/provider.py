from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Provider(TimestampMixin, Base):
    """User-configured AI provider instance stored locally."""

    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    provider_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    connection_status: Mapped[str] = mapped_column(
        String(32), default="untested", index=True, nullable=False
    )
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    credentials: Mapped[list["ProviderCredential"]] = relationship(
        back_populates="provider",
        cascade="all, delete-orphan",
        order_by="ProviderCredential.created_at",
    )
    models: Mapped[list["ProviderModel"]] = relationship(
        back_populates="provider",
        cascade="all, delete-orphan",
        order_by="ProviderModel.model_id",
    )


class ProviderCredential(TimestampMixin, Base):
    """Encrypted API credential belonging to a configured AI provider.

    Plaintext API keys are NEVER stored in SQLite; only Fernet ciphertext and a
    masked display fingerprint (e.g., `sk-****abcd`) are persisted.
    """

    __tablename__ = "provider_credentials"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    provider_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("providers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    credential_name: Mapped[str] = mapped_column(
        String(120), default="Default Key", nullable=False
    )
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    key_fingerprint: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    provider: Mapped["Provider"] = relationship(back_populates="credentials")


class ProviderModel(TimestampMixin, Base):
    """Discovered or manually registered model belonging to a configured provider."""

    __tablename__ = "provider_models"
    __table_args__ = (
        UniqueConstraint("provider_id", "model_id", name="uq_provider_models_pair"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    provider_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("providers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    model_id: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    capabilities: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    provider: Mapped["Provider"] = relationship(back_populates="models")
