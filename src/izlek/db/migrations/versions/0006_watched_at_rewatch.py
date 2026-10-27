"""Movie/TV watched_at timestamps and rewatch counts on user_media."""

import sqlalchemy as sa
from alembic import op

revision = "0006_watched_at_rewatch"
down_revision = "0005_personal_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_media") as batch:
        batch.add_column(sa.Column("watched_at", sa.DateTime(), nullable=True))
        batch.add_column(
            sa.Column(
                "rewatch_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("user_media") as batch:
        batch.drop_column("rewatch_count")
        batch.drop_column("watched_at")
