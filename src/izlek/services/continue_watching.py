"""Offline selection of the next released episode for tracked TV shows."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import TrackingStatus
from izlek.repositories.local import EpisodeRepository


@dataclass(frozen=True)
class ContinueWatchingItem:
    tmdb_id: int
    title: str
    poster_path: str
    backdrop_path: str
    season_number: int
    episode_number: int
    episode_title: str
    watched_count: int
    aired_count: int


class ContinueWatchingService:
    """Read local progress and select one next episode per eligible show."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._factory = session_factory
        self._owned_engine: Engine | None = None

    def _sessions(self) -> sessionmaker[Session]:
        if self._factory is None:
            self._owned_engine = initialize_database()
            self._factory = create_session_factory(self._owned_engine)
        return self._factory

    def list_next(self, *, today: date | None = None) -> list[ContinueWatchingItem]:
        """Ignore specials, undated and future episodes, and completed shows."""
        current_day = today or date.today()
        with self._sessions()() as session:
            rows = EpisodeRepository(session).list_continue_candidates()
            grouped = defaultdict(list)
            for media, user, season, episode, progress in rows:
                grouped[media.id].append((media, user, season, episode, progress))

            result = []
            for entries in grouped.values():
                media, user, _, _, _ = entries[0]
                # A regular episode progress row or WATCHING status starts a show.
                if not (user and user.status == TrackingStatus.WATCHING) and not any(
                    progress is not None for _, _, _, _, progress in entries
                ):
                    continue
                seen = set()
                aired = []
                for _, _, season, episode, progress in entries:
                    key = (season.season_number, episode.episode_number)
                    if key in seen:
                        continue
                    seen.add(key)
                    if episode.air_date is None or episode.air_date > current_day:
                        continue
                    aired.append((season, episode, bool(progress and progress.watched)))
                watched_count = sum(watched for _, _, watched in aired)
                next_episode = next(
                    (
                        (season, episode)
                        for season, episode, watched in aired
                        if not watched
                    ),
                    None,
                )
                if next_episode is None:
                    continue
                season, episode = next_episode
                result.append(
                    ContinueWatchingItem(
                        tmdb_id=media.tmdb_id,
                        title=media.original_title,
                        poster_path=media.poster_path or "",
                        backdrop_path=media.backdrop_path or "",
                        season_number=season.season_number,
                        episode_number=episode.episode_number,
                        episode_title=episode.name or "",
                        watched_count=watched_count,
                        aired_count=len(aired),
                    )
                )
            return result

    def close(self) -> None:
        if self._owned_engine is not None:
            self._owned_engine.dispose()
