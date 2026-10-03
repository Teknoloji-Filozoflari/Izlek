"""Create metadata and single-user tracking tables.

Revision ID: 0001_initial
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column(
            "media_type",
            sa.Enum(
                "MOVIE",
                "TV",
                name="mediatype",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("original_title", sa.String(500), nullable=False),
        sa.Column("original_language", sa.String(20)),
        sa.Column("overview", sa.Text()),
        sa.Column("poster_path", sa.String(500)),
        sa.Column("backdrop_path", sa.String(500)),
        sa.Column("release_date", sa.Date()),
        sa.Column("first_air_date", sa.Date()),
        sa.Column("runtime", sa.Integer()),
        sa.Column("metadata", sa.JSON()),
        sa.Column("last_synced_at", sa.DateTime()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("tmdb_id", "media_type"),
    )
    op.create_table(
        "user_media",
        sa.Column(
            "media_id",
            sa.Integer(),
            sa.ForeignKey("media_item.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PLANNED",
                "WATCHING",
                "WATCHED",
                name="trackingstatus",
                native_enum=False,
                create_constraint=True,
            ),
        ),
        sa.Column(
            "favorite", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "added_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_table(
        "season",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "media_id",
            sa.Integer(),
            sa.ForeignKey("media_item.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tmdb_season_id", sa.Integer()),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(500)),
        sa.Column("overview", sa.Text()),
        sa.Column("poster_path", sa.String(500)),
        sa.Column("air_date", sa.Date()),
        sa.UniqueConstraint("media_id", "season_number"),
        sa.UniqueConstraint("media_id", "tmdb_season_id"),
    )
    op.create_table(
        "episode",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("season.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tmdb_episode_id", sa.Integer()),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(500)),
        sa.Column("overview", sa.Text()),
        sa.Column("air_date", sa.Date()),
        sa.Column("runtime", sa.Integer()),
        sa.Column("still_path", sa.String(500)),
        sa.UniqueConstraint("season_id", "episode_number"),
        sa.UniqueConstraint("season_id", "tmdb_episode_id"),
    )
    op.create_table(
        "episode_progress",
        sa.Column(
            "episode_id",
            sa.Integer(),
            sa.ForeignKey("episode.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("watched", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("watched_at", sa.DateTime()),
    )
    op.create_table(
        "custom_list",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_table(
        "custom_list_item",
        sa.Column(
            "list_id",
            sa.Integer(),
            sa.ForeignKey("custom_list.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "media_id",
            sa.Integer(),
            sa.ForeignKey("media_item.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    for table in (
        "custom_list_item",
        "custom_list",
        "episode_progress",
        "episode",
        "season",
        "user_media",
        "media_item",
    ):
        op.drop_table(table)
