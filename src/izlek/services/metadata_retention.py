"""Expire remote metadata while retaining all personal rows and identities."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import Episode, MediaItem, MediaType, Season

METADATA_RETENTION = timedelta(days=180)
_MEDIA_FIELDS = (
    "original_language",
    "overview",
    "poster_path",
    "backdrop_path",
    "release_date",
    "first_air_date",
    "runtime",
    "metadata_json",
    "last_synced_at",
)
_SEASON_FIELDS = (
    "tmdb_season_id",
    "name",
    "overview",
    "poster_path",
    "air_date",
    "last_synced_at",
)
_EPISODE_FIELDS = (
    "tmdb_episode_id",
    "name",
    "overview",
    "air_date",
    "runtime",
    "still_path",
)
_OPTIONAL_SECTIONS = ("credits", "videos", "providers", "similar", "recommendations")
_SECTION_TIMES = "_section_synced_at"


def _section_time(blob: dict, section: str, fallback: datetime) -> datetime:
    times = blob.get(_SECTION_TIMES) or {}
    if not isinstance(times, dict):
        return fallback
    try:
        timestamp = datetime.fromisoformat(times[section])
    except (KeyError, ValueError, TypeError):
        return fallback
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(UTC).replace(tzinfo=None)
    return timestamp


def prune_optional_sections(blob: dict, fallback: datetime, cutoff: datetime) -> dict:
    """Age optional responses separately from successful main-detail refreshes."""
    retained = dict(blob)
    raw_times = blob.get(_SECTION_TIMES)
    times = dict(raw_times) if isinstance(raw_times, dict) else {}
    for section in _OPTIONAL_SECTIONS:
        if section in blob:
            timestamp = _section_time(blob, section, fallback)
            if timestamp <= cutoff:
                retained.pop(section)
                times.pop(section, None)
            else:
                times[section] = timestamp.isoformat()
    if times:
        retained[_SECTION_TIMES] = times
    else:
        retained.pop(_SECTION_TIMES, None)
    return retained


def merge_remote_metadata(
    existing: MediaItem | None, fresh: dict, now: datetime
) -> dict:
    """Retain valid optional cache without resetting failed endpoint timestamps."""
    previous = (
        prune_optional_sections(
            existing.metadata_json or {},
            existing.last_synced_at or existing.created_at,
            now - METADATA_RETENTION,
        )
        if existing is not None
        else {}
    )
    times = dict(previous.get(_SECTION_TIMES) or {})
    for section in _OPTIONAL_SECTIONS:
        if section in fresh:
            times[section] = now.isoformat()
    return {**previous, **fresh, _SECTION_TIMES: times}


def _clear(record: object, fields: tuple[str, ...]) -> bool:
    changed = False
    for field in fields:
        if getattr(record, field) is not None:
            setattr(record, field, None)
            changed = True
    return changed


class MetadataRetentionService:
    """Clear disposable TMDB fields without deleting tracking or progress keys."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._factory = session_factory
        self._owned_engine: Engine | None = None

    def prune(self, *, now: datetime | None = None) -> int:
        current = now or datetime.now(UTC)
        if current.tzinfo is not None:
            current = current.astimezone(UTC).replace(tzinfo=None)
        cutoff = current - METADATA_RETENTION
        if self._factory is None:
            self._owned_engine = initialize_database()
            self._factory = create_session_factory(self._owned_engine)
        changed = 0
        with self._factory.begin() as session:
            # Hold the write lock while checking timestamps so a concurrent
            # refresh cannot be overwritten using an earlier expiry decision.
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            media = list(session.scalars(select(MediaItem)))
            media_created = {item.id: item.created_at for item in media}
            seasons = list(session.scalars(select(Season)))
            episodes = list(session.scalars(select(Episode)))
            expired_media = set()
            for item in media:
                timestamp = item.last_synced_at or item.created_at
                if timestamp > cutoff:
                    if item.metadata_json:
                        retained = prune_optional_sections(
                            item.metadata_json, timestamp, cutoff
                        )
                        if retained != item.metadata_json:
                            item.metadata_json = retained
                            changed += 1
                    continue
                expired_media.add(item.id)
                label = "Film" if item.media_type == MediaType.MOVIE else "Dizi"
                placeholder = f"{label} #{item.tmdb_id}"
                renamed = item.original_title != placeholder
                cleared = _clear(item, _MEDIA_FIELDS)
                if renamed or cleared:
                    item.original_title = placeholder
                    changed += 1
            expired_seasons = set()
            for season in seasons:
                expired = (
                    season.last_synced_at <= cutoff
                    if season.last_synced_at is not None
                    else season.media_id in expired_media
                    or media_created[season.media_id] <= cutoff
                )
                if expired:
                    expired_seasons.add(season.id)
                    changed += _clear(season, _SEASON_FIELDS)
            for episode in episodes:
                if episode.season_id in expired_seasons:
                    changed += _clear(episode, _EPISODE_FIELDS)
        return changed

    def close(self) -> None:
        if self._owned_engine is not None:
            self._owned_engine.dispose()
