"""Create dynamic AI provider management tables (providers, provider_credentials, provider_models).

Revision ID: 0003_provider_management_tables
Revises: 0002_core_workspace_tables
Create Date: 2026-01-03 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_provider_management_tables"
down_revision: str | None = "0002_core_workspace_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "providers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_key", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("provider_type", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("default_model", sa.String(length=160), nullable=True),
        sa.Column("connection_status", sa.String(length=32), nullable=False),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_providers"),
    )
    op.create_index("ix_providers_provider_key", "providers", ["provider_key"], unique=False)
    op.create_index("ix_providers_provider_type", "providers", ["provider_type"], unique=False)
    op.create_index(
        "ix_providers_connection_status", "providers", ["connection_status"], unique=False
    )

    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("credential_name", sa.String(length=120), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("key_fingerprint", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["providers.id"],
            name="fk_provider_credentials_provider_id_providers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_provider_credentials"),
    )
    op.create_index(
        "ix_provider_credentials_provider_id",
        "provider_credentials",
        ["provider_id"],
        unique=False,
    )

    op.create_table(
        "provider_models",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("model_id", sa.String(length=160), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("is_manual", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["providers.id"],
            name="fk_provider_models_provider_id_providers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_provider_models"),
        sa.UniqueConstraint("provider_id", "model_id", name="uq_provider_models_pair"),
    )
    op.create_index(
        "ix_provider_models_provider_id", "provider_models", ["provider_id"], unique=False
    )
    op.create_index(
        "ix_provider_models_model_id", "provider_models", ["model_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("provider_models")
    op.drop_table("provider_credentials")
    op.drop_table("providers")
