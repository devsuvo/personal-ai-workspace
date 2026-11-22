"""Add multi-provider chat metadata columns to messages table.

Revision ID: 0004_chat_message_fields
Revises: 0003_provider_management_tables
Create Date: 2026-01-04 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_chat_message_fields"
down_revision: str | None = "0003_provider_management_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("provider_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("model_id", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("credential_id", sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="completed",
            )
        )
        batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))
        batch_op.create_index("ix_messages_provider_id", ["provider_id"], unique=False)
        batch_op.create_index("ix_messages_status", ["status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_index("ix_messages_status")
        batch_op.drop_index("ix_messages_provider_id")
        batch_op.drop_column("error_message")
        batch_op.drop_column("status")
        batch_op.drop_column("credential_id")
        batch_op.drop_column("model_id")
        batch_op.drop_column("provider_id")
