from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.project import Project


class Artifact(TimestampMixin, Base):
    """Standalone document, code, HTML, JSON, CSV, or text artifact saved locally."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    artifact_type: Mapped[str] = mapped_column(
        String(32), default="markdown", index=True, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)

    project: Mapped["Project | None"] = relationship(back_populates="artifacts")
    conversation: Mapped["Conversation | None"] = relationship()
