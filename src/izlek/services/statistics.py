"""Local-only viewing statistics with explicit missing-runtime handling."""

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaItem, MediaType, TrackingStatus, UserMedia
from izlek.repositories.local import StatisticsRepository


@dataclass(frozen=True)
class StatisticsSnapshot:
    """All aggregate values shown in the local statistics UI."""

    watched_movies: int
    completed_tv: int
    watched_episodes: int
    watched_movie_minutes: int | None
    watched_episode_minutes: int | None
    estimated_total_minutes: int | None
    missing_movie_runtime_count: int
    missing_episode_runtime_count: int
    favorite_movies: int
    favorite_tv: int
    planned_movies: int
    planned_tv: int
    top_genres: list[dict[str, int | str]]

    def as_dict(self) -> dict[str, Any]:
        """Return QML-safe values without exposing ORM records."""
        return asdict(self)


def _runtime_total(runtimes: list[int | None]) -> tuple[int | None, int]:
    missing = sum(runtime is None or runtime <= 0 for runtime in runtimes)
    if missing:
        return None, missing
    return sum(runtime or 0 for runtime in runtimes), 0


def _genres(media: MediaItem) -> list[str]:
    detail = (media.metadata_json or {}).get("detail") or {}
    raw_genres = detail.get("genres", []) if isinstance(detail, dict) else []
    if not isinstance(raw_genres, list):
        return []
    names = []
    for genre in raw_genres:
        if isinstance(genre, dict) and isinstance(genre.get("name"), str):
            name = genre["name"].strip()
            if name:
                names.append(name)
    return names


def _is_watched_media(media: MediaItem, user: UserMedia) -> bool:
    return user.status == TrackingStatus.WATCHED and media.media_type in {
        MediaType.MOVIE,
        MediaType.TV,
    }


class StatisticsService:
    """Calculate durable viewing aggregates from SQLite without TMDb requests."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._factory = session_factory
        self._owned_engine: Engine | None = None

    def _sessions(self) -> sessionmaker[Session]:
        if self._factory is None:
            self._owned_engine = initialize_database()
            self._factory = create_session_factory(self._owned_engine)
        return self._factory

    def snapshot(self) -> StatisticsSnapshot:
        """Return local aggregates and hide duration totals when data is incomplete."""
        with self._sessions()() as session:
            repository = StatisticsRepository(session)
            tracked = repository.media_with_tracking()
            watched_episodes = repository.watched_episodes()

        watched_movies = [
            media
            for media, user in tracked
            if media.media_type == MediaType.MOVIE and _is_watched_media(media, user)
        ]
        completed_tv = [
            media
            for media, user in tracked
            if media.media_type == MediaType.TV and _is_watched_media(media, user)
        ]
        movie_minutes, missing_movies = _runtime_total(
            [media.runtime for media in watched_movies]
        )
        episode_minutes, missing_episodes = _runtime_total(
            [episode.runtime for episode in watched_episodes]
        )
        estimated_total = (
            movie_minutes + episode_minutes
            if movie_minutes is not None and episode_minutes is not None
            else None
        )
        genres = Counter(
            genre
            for media, user in tracked
            if _is_watched_media(media, user)
            for genre in set(_genres(media))
        )
        return StatisticsSnapshot(
            watched_movies=len(watched_movies),
            completed_tv=len(completed_tv),
            watched_episodes=len(watched_episodes),
            watched_movie_minutes=movie_minutes,
            watched_episode_minutes=episode_minutes,
            estimated_total_minutes=estimated_total,
            missing_movie_runtime_count=missing_movies,
            missing_episode_runtime_count=missing_episodes,
            favorite_movies=sum(
                media.media_type == MediaType.MOVIE and user.favorite
                for media, user in tracked
            ),
            favorite_tv=sum(
                media.media_type == MediaType.TV and user.favorite
                for media, user in tracked
            ),
            planned_movies=sum(
                media.media_type == MediaType.MOVIE
                and user.status == TrackingStatus.PLANNED
                for media, user in tracked
            ),
            planned_tv=sum(
                media.media_type == MediaType.TV
                and user.status == TrackingStatus.PLANNED
                for media, user in tracked
            ),
            top_genres=[
                {"name": name, "count": count}
                for name, count in sorted(
                    genres.items(), key=lambda item: (-item[1], item[0].casefold())
                )[:5]
            ],
        )

    def close(self) -> None:
        if self._owned_engine is not None:
            self._owned_engine.dispose()
