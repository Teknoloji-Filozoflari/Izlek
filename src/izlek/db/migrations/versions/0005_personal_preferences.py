"""Personal ratings, notes and independent recommendation dismissal."""

import sqlalchemy as sa
from alembic import op

revision = "0005_personal_preferences"
down_revision = "0004_library_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_media") as batch:
        batch.add_column(sa.Column("personal_rating", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("personal_note", sa.Text(), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column(
                "dismissed", sa.Boolean(), nullable=False, server_default=sa.text("0")
            )
        )
        batch.create_check_constraint(
            "ck_user_personal_rating",
            "personal_rating IS NULL OR personal_rating BETWEEN 1 AND 10",
        )


def downgrade() -> None:
    with op.batch_alter_table("user_media") as batch:
        batch.drop_constraint("ck_user_personal_rating", type_="check")
        batch.drop_column("dismissed")
        batch.drop_column("personal_note")
        batch.drop_column("personal_rating")
