"""Episode-level last successful TMDb fetch timestamp."""

import sqlalchemy as sa
from alembic import op

revision = "0008_episode_freshness"
down_revision = "0007_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("episode", sa.Column("last_synced_at", sa.DateTime()))


def downgrade() -> None:
    op.drop_column("episode", "last_synced_at")
