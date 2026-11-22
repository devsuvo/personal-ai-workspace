"""Add conversation pinning, prompt_templates, and model_pricing tables.

Revision ID: 0006_productivity_prompts_analytics
Revises: 0005_projects_files_artifacts
Create Date: 2026-01-06 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0006_productivity_prompts_analytics"
down_revision: str | None = "0005_projects_files_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_index("ix_conversations_is_pinned", ["is_pinned"], unique=False)

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_prompt_templates"),
    )
    op.create_index("ix_prompt_templates_title", "prompt_templates", ["title"], unique=False)
    op.create_index("ix_prompt_templates_category", "prompt_templates", ["category"], unique=False)
    op.create_index(
        "ix_prompt_templates_is_favorite", "prompt_templates", ["is_favorite"], unique=False
    )

    op.create_table(
        "model_pricing",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=False),
        sa.Column("model_name", sa.String(length=160), nullable=False),
        sa.Column("input_cost_per_1m", sa.Float(), nullable=False),
        sa.Column("output_cost_per_1m", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_model_pricing"),
        sa.UniqueConstraint(
            "provider_name", "model_name", name="uq_model_pricing_provider_model"
        ),
    )
    op.create_index(
        "ix_model_pricing_provider_name", "model_pricing", ["provider_name"], unique=False
    )
    op.create_index(
        "ix_model_pricing_model_name", "model_pricing", ["model_name"], unique=False
    )


def downgrade() -> None:
    op.drop_table("model_pricing")
    op.drop_table("prompt_templates")
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.drop_index("ix_conversations_is_pinned")
        batch_op.drop_column("is_pinned")
