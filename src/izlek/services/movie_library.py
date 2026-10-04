"""Offline movie library filtering, sorting, favorites and statistics."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaItem, MediaType, TrackingStatus, UserMedia
from izlek.repositories.local import MediaRepository
from izlek.services.library_common import (
    SORT_OPTIONS,
    SORT_RECENT,
    metadata_score,
    sort_items,
    status_counts,
)


@dataclass(frozen=True)
class MovieLibraryItem:
    tmdb_id: int
    title: str
    year: str
    score: float | None
    poster_path: str
    status: str
    favorite: bool
    added_at: datetime


@dataclass(frozen=True)
class MovieLibrarySnapshot:
    items: list[MovieLibraryItem]
    favorites: list[MovieLibraryItem]
    stats: dict[str, int]


def _item(media: MediaItem, user: UserMedia) -> MovieLibraryItem:
    return MovieLibraryItem(
        tmdb_id=media.tmdb_id,
        title=media.original_title,
        year=str(media.release_date.year) if media.release_date else "",
        score=metadata_score(media),
        poster_path=media.poster_path or "",
        status=user.status.value if user.status else "",
        favorite=user.favorite,
        added_at=user.added_at,
    )


class MovieLibraryService:
    """Read the user's locally tracked movies without requesting TMDb."""

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
    ) -> MovieLibrarySnapshot:
        """Return one status grid plus favorites and all tracked movie counts."""
        if sort_by not in SORT_OPTIONS:
            raise ValueError(f"Bilinmeyen sıralama: {sort_by}")
        status = TrackingStatus(status) if status is not None else None
        with self._sessions()() as session:
            entries = [
                _item(media, user)
                for media, user in MediaRepository(session).list_local_media(
                    MediaType.MOVIE
                )
            ]
        tracked = [item for item in entries if item.status]
        return MovieLibrarySnapshot(
            items=sort_items(
                [item for item in tracked if status is None or item.status == status],
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
