"""Local favorites shared by movie, TV, home and library views."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaItem, MediaType
from izlek.repositories.local import MediaRepository, UserMediaRepository


@dataclass(frozen=True)
class FavoriteItem:
    tmdb_id: int
    kind: str
    title: str
    year: str
    poster_path: str
    status: str
    favorite: bool
    added_at: datetime


def _year(media: MediaItem) -> str:
    date_value = (
        media.release_date
        if media.media_type == MediaType.MOVIE
        else media.first_air_date
    )
    return str(date_value.year) if date_value else ""


class FavoritesService:
    """Read and change favorites in SQLite without changing tracking status."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._factory = session_factory
        self._owned_engine: Engine | None = None

    def _sessions(self) -> sessionmaker[Session]:
        if self._factory is None:
            self._owned_engine = initialize_database()
            self._factory = create_session_factory(self._owned_engine)
        return self._factory

    def list_all(self) -> list[FavoriteItem]:
        """Return favorites of both media types, newest local additions first."""
        with self._sessions()() as session:
            rows = [
                (media, user)
                for kind in (MediaType.MOVIE, MediaType.TV)
                for media, user in MediaRepository(session).list_local_media(kind)
                if user.favorite
            ]
            items = [
                FavoriteItem(
                    tmdb_id=media.tmdb_id,
                    kind=media.media_type.value.lower(),
                    title=media.original_title,
                    year=_year(media),
                    poster_path=media.poster_path or "",
                    status=user.status.value if user.status else "",
                    favorite=True,
                    added_at=user.added_at,
                )
                for media, user in rows
            ]
        return sorted(
            items,
            key=lambda item: (-item.added_at.timestamp(), item.kind, -item.tmdb_id),
        )

    def set_favorite(self, kind: str, tmdb_id: int, favorite: bool) -> None:
        """Update a known local item by its TMDb identity and media type."""
        media_type = MediaType(kind.upper())
        with self._sessions().begin() as session:
            media = MediaRepository(session).get_by_tmdb(tmdb_id, media_type)
            if media is None:
                raise LookupError(f"Medya bulunamadı: {kind}/{tmdb_id}")
            UserMediaRepository(session).set_favorite(media.id, favorite)

    def close(self) -> None:
        if self._owned_engine is not None:
            self._owned_engine.dispose()
