"""Offline TV library with regular-season episode progress."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaItem, MediaType, TrackingStatus, UserMedia
from izlek.repositories.local import EpisodeRepository, MediaRepository
from izlek.services.library_common import (
    SORT_OPTIONS,
    SORT_RECENT,
    metadata_score,
    sort_items,
    status_counts,
)


@dataclass(frozen=True)
class TvLibraryItem:
    tmdb_id: int
    title: str
    year: str
    score: float | None
    poster_path: str
    status: str
    favorite: bool
    added_at: datetime
    progress: float
    progress_text: str
    watched_count: int
    episode_count: int


@dataclass(frozen=True)
class TvLibrarySnapshot:
    items: list[TvLibraryItem]
    favorites: list[TvLibraryItem]
    stats: dict[str, int]


def _expected_episodes(media: MediaItem) -> int:
    """Use the saved TMDb season summaries, excluding season zero."""
    detail = (media.metadata_json or {}).get("detail") or {}
    if not isinstance(detail, dict):
        return 0
    seasons = detail.get("seasons") or []
    if not isinstance(seasons, list):
        return 0
    total = 0
    for season in seasons:
        if not isinstance(season, dict):
            continue
        number = season.get("season_number")
        count = season.get("episode_count")
        if isinstance(number, int) and number > 0 and isinstance(count, int):
            total += max(0, count)
    return total


def _item(
    media: MediaItem,
    user: UserMedia,
    episodes: list[tuple[int, int, date | None, bool]],
    today: date,
) -> TvLibraryItem:
    seen = set()
    regular = []
    for season_number, episode_number, air_date, watched in episodes:
        key = (season_number, episode_number)
        if key not in seen:
            seen.add(key)
            regular.append((season_number, episode_number, air_date, watched))
    watched_count = sum(watched for _, _, _, watched in regular)
    total = max(_expected_episodes(media), len(regular))
    next_aired = next(
        (
            (season_number, episode_number)
            for season_number, episode_number, air_date, watched in regular
            if not watched and air_date is not None and air_date <= today
        ),
        None,
    )
    if next_aired is not None:
        progress_text = f"S{next_aired[0]:02d}E{next_aired[1]:02d}"
    elif total:
        progress_text = f"{watched_count} / {total} bölüm"
    else:
        progress_text = ""
    return TvLibraryItem(
        tmdb_id=media.tmdb_id,
        title=media.original_title,
        year=str(media.first_air_date.year) if media.first_air_date else "",
        score=metadata_score(media),
        poster_path=media.poster_path or "",
        status=user.status.value if user.status else "",
        favorite=user.favorite,
        added_at=user.added_at,
        progress=watched_count / total if total else -1,
        progress_text=progress_text,
        watched_count=watched_count,
        episode_count=total,
    )


class TvLibraryService:
    """Read tracked TV shows, favorites and local episode progress."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._factory = session_factory
        self._owned_engine: Engine | None = None

    def _sessions(self) -> sessionmaker[Session]:
        if self._factory is None:
            self._owned_engine = initialize_database()
            self._factory = create_session_factory(self._owned_engine)
        return self._factory

    def snapshot(
        self,
        status: TrackingStatus | None = TrackingStatus.PLANNED,
        sort_by: str = SORT_RECENT,
        *,
        today: date | None = None,
    ) -> TvLibrarySnapshot:
        """Build a status grid and independent favorites from local data."""
        if sort_by not in SORT_OPTIONS:
            raise ValueError(f"Bilinmeyen sıralama: {sort_by}")
        status = TrackingStatus(status) if status is not None else None
        current_day = today or date.today()
        with self._sessions()() as session:
            media_rows = MediaRepository(session).list_local_media(MediaType.TV)
            episode_rows = EpisodeRepository(session).list_continue_candidates(
                {media.id for media, _ in media_rows}
            )
            grouped = defaultdict(list)
            for media, _, season, episode, progress in episode_rows:
                grouped[media.id].append(
                    (
                        season.season_number,
                        episode.episode_number,
                        episode.air_date,
                        bool(progress and progress.watched),
                    )
                )
            entries = [
                _item(media, user, grouped[media.id], current_day)
                for media, user in media_rows
            ]
        return TvLibrarySnapshot(
            items=sort_items(
                [
                    item
                    for item in entries
                    if item.status and (status is None or item.status == status)
                ],
                sort_by,
            ),
            favorites=sort_items(
                [item for item in entries if item.favorite], SORT_RECENT
            ),
            stats=status_counts(entries),
        )

    def close(self) -> None:
        if self._owned_engine is not None:
            self._owned_engine.dispose()
