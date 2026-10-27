"""User tags for local media items."""

import sqlalchemy as sa
from alembic import op

revision = "0007_tags"
down_revision = "0006_watched_at_rewatch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tag",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "media_tag",
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("media_id", sa.Integer(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_id"], ["media_item.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tag_id", "media_id"),
    )


def downgrade() -> None:
    op.drop_table("media_tag")
    op.drop_table("tag")
