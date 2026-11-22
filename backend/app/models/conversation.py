from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.message import Message
    from app.models.project import Project
    from app.models.usage_log import UsageLog


class Conversation(TimestampMixin, Base):
    """A local chat conversation optionally associated with a project and provider."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(
        String(255), default="New Conversation", nullable=False
    )
    provider_id: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    model_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )

    project: Mapped["Project | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="conversation",
        passive_deletes=True,
    )
    usage_logs: Mapped[list["UsageLog"]] = relationship(
        back_populates="conversation",
        passive_deletes=True,
    )
