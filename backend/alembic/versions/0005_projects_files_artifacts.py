"""Extend projects & attachments and create artifacts table.

Revision ID: 0005_projects_files_artifacts
Revises: 0004_chat_message_fields
Create Date: 2026-01-05 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_projects_files_artifacts"
down_revision: str | None = "0004_chat_message_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("icon", sa.String(length=40), nullable=False, server_default="folder")
        )
        batch_op.add_column(
            sa.Column(
                "color", sa.String(length=32), nullable=False, server_default="terracotta"
            )
        )
        batch_op.add_column(
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_index("ix_projects_is_archived", ["is_archived"], unique=False)

    with op.batch_alter_table("attachments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "extraction_status",
                sa.String(length=32),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(
            sa.Column("extracted_text_reference", sa.String(length=512), nullable=True)
        )
        batch_op.add_column(sa.Column("extraction_error", sa.Text(), nullable=True))
        batch_op.create_index(
            "ix_attachments_extraction_status", ["extraction_status"], unique=False
        )

    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("artifact_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_artifacts_project_id_projects",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_artifacts_conversation_id_conversations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_artifacts"),
    )
    op.create_index("ix_artifacts_project_id", "artifacts", ["project_id"], unique=False)
    op.create_index(
        "ix_artifacts_conversation_id", "artifacts", ["conversation_id"], unique=False
    )
    op.create_index("ix_artifacts_title", "artifacts", ["title"], unique=False)
    op.create_index(
        "ix_artifacts_artifact_type", "artifacts", ["artifact_type"], unique=False
    )


def downgrade() -> None:
    op.drop_table("artifacts")
    with op.batch_alter_table("attachments", schema=None) as batch_op:
        batch_op.drop_index("ix_attachments_extraction_status")
        batch_op.drop_column("extraction_error")
        batch_op.drop_column("extracted_text_reference")
        batch_op.drop_column("extraction_status")
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_index("ix_projects_is_archived")
        batch_op.drop_column("is_archived")
        batch_op.drop_column("color")
        batch_op.drop_column("icon")
