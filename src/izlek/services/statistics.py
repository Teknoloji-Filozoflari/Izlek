"""Local-only viewing statistics with explicit missing-runtime handling."""

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaItem, MediaType, TrackingStatus, UserMedia
from izlek.repositories.local import StatisticsRepository

_HISTORY_LIMIT = 40
_MONTH_NAMES = [
    "Oca",
    "Şub",
    "Mar",
    "Nis",
    "May",
    "Haz",
    "Tem",
    "Ağu",
    "Eyl",
    "Eki",
    "Kas",
    "Ara",
]


@dataclass(frozen=True)
class StatisticsSnapshot:
    """All aggregate values shown in the local statistics UI."""

    watched_movies: int
    completed_tv: int
    watched_episodes: int
    watched_movie_minutes: int
    watched_episode_minutes: int
    estimated_total_minutes: int
    missing_movie_runtime_count: int
    missing_episode_runtime_count: int
    favorite_movies: int
    favorite_tv: int
    planned_movies: int
    planned_tv: int
    movie_rewatch_count: int
    top_genres: list[dict[str, int | str]]
    monthly_activity: list[dict[str, Any]] = field(default_factory=list)
    top_shows: list[dict[str, Any]] = field(default_factory=list)
    genre_distribution: list[dict[str, Any]] = field(default_factory=list)
    recent_history: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Return QML-safe values without exposing ORM records."""
        return asdict(self)


def _runtime_total(runtimes: list[int | None]) -> tuple[int, int]:
    """Sum known positive runtimes and count entries excluded from duration."""
    missing = sum(runtime is None or runtime <= 0 for runtime in runtimes)
    return sum(runtime for runtime in runtimes if runtime and runtime > 0), missing


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


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.replace(microsecond=0).isoformat() + "Z"


def _empty_months(current: date) -> dict[tuple[int, int], dict[str, Any]]:
    month_index = current.year * 12 + current.month - 1
    months: dict[tuple[int, int], dict[str, Any]] = {}
    for index in range(month_index - 11, month_index + 1):
        year, month = divmod(index, 12)
        months[(year, month + 1)] = {
            "label": _MONTH_NAMES[month],
            "year": year,
            "month": month + 1,
            "minutes": 0,
            "episodes": 0,
            "movies": 0,
            "movie_minutes": 0,
            "missing_runtime": 0,
        }
    return months


def _add_month(
    months: dict[tuple[int, int], dict[str, Any]],
    watched_at: datetime | None,
    *,
    minutes: int,
    missing: bool,
    movies: int = 0,
    episodes: int = 0,
) -> None:
    if watched_at is None:
        return
    month = months.get((watched_at.year, watched_at.month))
    if month is None:
        return
    month["minutes"] += minutes
    month["movies"] += movies
    month["episodes"] += episodes
    if movies:
        month["movie_minutes"] += minutes
    month["missing_runtime"] += bool(missing)


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

    def snapshot(self, *, today: date | None = None) -> StatisticsSnapshot:
        """Return local aggregates using only known runtimes for durations."""
        with self._sessions()() as session:
            repository = StatisticsRepository(session)
            tracked = repository.media_with_tracking()
            activity = repository.watched_episode_activity()
            watched_episodes = [episode for _, _, episode, _ in activity]

        watched_movies = [
            (media, user)
            for media, user in tracked
            if media.media_type == MediaType.MOVIE and _is_watched_media(media, user)
        ]
        completed_tv = [
            media
            for media, user in tracked
            if media.media_type == MediaType.TV and _is_watched_media(media, user)
        ]
        movie_minutes, missing_movies = _runtime_total(
            [media.runtime for media, _ in watched_movies]
        )
        episode_minutes, missing_episodes = _runtime_total(
            [episode.runtime for episode in watched_episodes]
        )
        estimated_total = movie_minutes + episode_minutes
        genres = Counter(
            genre
            for media, user in tracked
            if _is_watched_media(media, user)
            for genre in set(_genres(media))
        )
        months = _empty_months(today or date.today())
        shows: dict[int, dict[str, Any]] = {}
        watched_show_media: dict[int, MediaItem] = {}
        history: list[dict[str, Any]] = []

        for media, user in watched_movies:
            known = media.runtime is not None and media.runtime > 0
            runtime = media.runtime if known else 0
            _add_month(
                months,
                user.watched_at,
                minutes=runtime,
                missing=not known,
                movies=1,
            )
            if user.watched_at:
                history.append(
                    {
                        "kind": "movie",
                        "id": media.tmdb_id,
                        "title": media.original_title,
                        "subtitle": (
                            media.release_date.isoformat()[:4]
                            if media.release_date
                            else "Film"
                        ),
                        "watchedAt": _iso(user.watched_at),
                        "minutes": runtime if known else None,
                        "posterPath": media.poster_path or "",
                        "rewatchCount": int(user.rewatch_count or 0),
                    }
                )

        for media, season, episode, progress in activity:
            watched_show_media[media.id] = media
            show = shows.setdefault(
                media.id,
                {
                    "id": media.tmdb_id,
                    "title": media.original_title,
                    "posterPath": media.poster_path or "",
                    "minutes": 0,
                    "episodes": 0,
                    "missing_runtime": 0,
                },
            )
            show["episodes"] += 1
            known = episode.runtime is not None and episode.runtime > 0
            show["minutes"] += episode.runtime if known else 0
            show["missing_runtime"] += not known
            _add_month(
                months,
                progress.watched_at,
                minutes=episode.runtime if known else 0,
                missing=not known,
                episodes=1,
            )
            if progress.watched_at:
                code = f"S{season.season_number:02d}E{episode.episode_number:02d}"
                history.append(
                    {
                        "kind": "episode",
                        "id": media.tmdb_id,
                        "title": media.original_title,
                        "subtitle": (
                            f"{code} · {episode.name}" if episode.name else code
                        ),
                        "watchedAt": _iso(progress.watched_at),
                        "minutes": episode.runtime if known else None,
                        "posterPath": media.poster_path or "",
                        "rewatchCount": 0,
                    }
                )

        genre_counts = Counter(
            genre
            for media in [media for media, _ in watched_movies]
            + list(watched_show_media.values())
            for genre in set(_genres(media))
        )
        ordered_genres = sorted(
            genre_counts.items(), key=lambda item: (-item[1], item[0].casefold())
        )
        if len(ordered_genres) > 5:
            ordered_genres = ordered_genres[:4] + [
                ("Diğer", sum(count for _, count in ordered_genres[4:]))
            ]
        genre_total = sum(genre_counts.values())
        history.sort(key=lambda item: item["watchedAt"], reverse=True)
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
            movie_rewatch_count=sum(
                int(user.rewatch_count or 0) for _, user in watched_movies
            ),
            top_genres=[
                {"name": name, "count": count}
                for name, count in sorted(
                    genres.items(), key=lambda item: (-item[1], item[0].casefold())
                )[:5]
            ],
            monthly_activity=list(months.values()),
            top_shows=sorted(
                shows.values(),
                key=lambda item: (-item["minutes"], item["title"].casefold()),
            )[:5],
            genre_distribution=[
                {"name": name, "count": count, "share": count / genre_total}
                for name, count in ordered_genres
            ],
            recent_history=history[:_HISTORY_LIMIT],
        )

    def close(self) -> None:
        if self._owned_engine is not None:
            self._owned_engine.dispose()
