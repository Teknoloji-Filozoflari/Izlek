"""Track the last successful season metadata refresh.

Revision ID: 0003_season_freshness
Revises: 0002_status_source
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_season_freshness"
down_revision = "0002_status_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("season", sa.Column("last_synced_at", sa.DateTime()))


def downgrade() -> None:
    op.drop_column("season", "last_synced_at")
