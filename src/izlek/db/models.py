"""Persistence models for local metadata and personal tracking data."""

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Return naive UTC for SQLite's timezone-free datetime storage."""
    return datetime.now(UTC).replace(tzinfo=None)


class MediaType(StrEnum):
    MOVIE = "MOVIE"
    TV = "TV"


class TrackingStatus(StrEnum):
    PLANNED = "PLANNED"
    WATCHING = "WATCHING"
    WATCHED = "WATCHED"


class Base(DeclarativeBase):
    pass


class MediaItem(Base):
    """TMDb metadata; never stores personal tracking state."""

    __tablename__ = "media_item"
    __table_args__ = (UniqueConstraint("tmdb_id", "media_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[MediaType] = mapped_column(
        SqlEnum(MediaType, native_enum=False, create_constraint=True), nullable=False
    )
    original_title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_language: Mapped[str | None] = mapped_column(String(20))
    overview: Mapped[str | None] = mapped_column(Text)
    poster_path: Mapped[str | None] = mapped_column(String(500))
    backdrop_path: Mapped[str | None] = mapped_column(String(500))
    release_date: Mapped[date | None] = mapped_column(Date)
    first_air_date: Mapped[date | None] = mapped_column(Date)
    runtime: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class UserMedia(Base):
    """One user's status and favorite flag for a media item."""

    __tablename__ = "user_media"

    media_id: Mapped[int] = mapped_column(
        ForeignKey("media_item.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[TrackingStatus | None] = mapped_column(
        SqlEnum(TrackingStatus, native_enum=False, create_constraint=True)
    )
    status_is_manual: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    favorite: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class Season(Base):
    """TMDb season metadata for a TV item."""

    __tablename__ = "season"
    __table_args__ = (
        UniqueConstraint("media_id", "season_number"),
        UniqueConstraint("media_id", "tmdb_season_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media_item.id", ondelete="CASCADE"), nullable=False
    )
    tmdb_season_id: Mapped[int | None] = mapped_column(Integer)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(500))
    overview: Mapped[str | None] = mapped_column(Text)
    poster_path: Mapped[str | None] = mapped_column(String(500))
    air_date: Mapped[date | None] = mapped_column(Date)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)


class Episode(Base):
    """TMDb episode metadata, independent of watched state."""

    __tablename__ = "episode"
    __table_args__ = (
        UniqueConstraint("season_id", "episode_number"),
        UniqueConstraint("season_id", "tmdb_episode_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("season.id", ondelete="CASCADE"), nullable=False
    )
    tmdb_episode_id: Mapped[int | None] = mapped_column(Integer)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(500))
    overview: Mapped[str | None] = mapped_column(Text)
    air_date: Mapped[date | None] = mapped_column(Date)
    runtime: Mapped[int | None] = mapped_column(Integer)
    still_path: Mapped[str | None] = mapped_column(String(500))


class EpisodeProgress(Base):
    """Local episode progress; metadata refreshes must leave it intact."""

    __tablename__ = "episode_progress"

    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episode.id", ondelete="CASCADE"), primary_key=True
    )
    watched: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    watched_at: Mapped[datetime | None] = mapped_column(DateTime)


class CustomList(Base):
    """A user-created ordered collection."""

    __tablename__ = "custom_list"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class CustomListItem(Base):
    """One media item in one custom list, with its own position."""

    __tablename__ = "custom_list_item"

    list_id: Mapped[int] = mapped_column(
        ForeignKey("custom_list.id", ondelete="CASCADE"), primary_key=True
    )
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media_item.id", ondelete="CASCADE"), primary_key=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
