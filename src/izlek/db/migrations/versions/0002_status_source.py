"""Track whether a status was chosen manually.

Revision ID: 0002_status_source
Revises: 0001_initial
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_status_source"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_media",
        sa.Column(
            "status_is_manual", sa.Boolean(), nullable=False,
            server_default=sa.text("0"),
        ),
    )
    # Before this revision every stored status came from a user action.
    op.execute(
        "UPDATE user_media SET status_is_manual = 1 WHERE status IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("user_media", "status_is_manual")
