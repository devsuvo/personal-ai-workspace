"""Initial foundation baseline migration.

Revision ID: 0001_initial_foundation
Revises:
Create Date: 2026-01-01 00:00:00
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001_initial_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Baseline revision establishing Alembic version tracking in SQLite.

    Domain tables (conversations, messages, projects, providers, api_credentials,
    models, attachments, usage_logs, app_settings) will be added in subsequent phases.
    """
    pass


def downgrade() -> None:
    pass
