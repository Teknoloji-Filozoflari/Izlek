"""Persist personal film/TV card ordering without altering tracking state."""

import sqlalchemy as sa
from alembic import op

revision = "0004_library_order"
down_revision = "0003_season_freshness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_media", sa.Column("sort_order", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_media", "sort_order")
