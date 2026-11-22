from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.artifact import Artifact
    from app.models.attachment import Attachment
    from app.models.conversation import Conversation


class Project(TimestampMixin, Base):
    """Logical workspace grouping conversations, instructions, files, and artifacts."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    icon: Mapped[str] = mapped_column(String(40), default="folder", nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="terracotta", nullable=False)
    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="project",
        passive_deletes=True,
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="project",
        passive_deletes=True,
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="project",
        passive_deletes=True,
    )
