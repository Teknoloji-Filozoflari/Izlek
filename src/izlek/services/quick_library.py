"""Add result summaries locally without loading a detail page or remote API."""

from datetime import date

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository


class QuickLibraryService:
    """Persist one-click additions while preserving existing personal state."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._factory = session_factory
        self._owned_engine: Engine | None = None

    def _sessions(self) -> sessionmaker[Session]:
        if self._factory is None:
            self._owned_engine = initialize_database()
            self._factory = create_session_factory(self._owned_engine)
        return self._factory

    def states(self) -> dict[str, str]:
        with self._sessions()() as session:
            repo = MediaRepository(session)
            return {
                f"{kind.value.lower()}:{media.tmdb_id}": "added"
                for kind in (MediaType.MOVIE, MediaType.TV)
                for media, user in repo.list_local_media(kind)
                if user.status is not None
            }

    def add(self, summary: dict) -> None:
        kind = MediaType(str(summary["mediaType"]).upper())
        item_id = int(summary["id"])
        title = str(summary["title"]).strip()
        if item_id <= 0 or not title:
            raise ValueError("Geçersiz medya")
        with self._sessions().begin() as session:
            # Serialize the existence check with other writes: repeated clicks
            # must never reset watched state or overwrite detailed metadata.
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            repo = MediaRepository(session)
            media = repo.get_by_tmdb(item_id, kind)
            if media is None:
                media = repo.upsert(
                    item_id, kind, title, poster_path=summary.get("posterPath") or None
                )
                raw_date = summary.get("releaseDate") or ""
                if raw_date:
                    try:
                        released = date.fromisoformat(raw_date)
                    except ValueError:
                        released = None
                    if kind == MediaType.MOVIE:
                        media.release_date = released
                    else:
                        media.first_air_date = released
                # A summary is not a freshly synced full detail response.
            users = UserMediaRepository(session)
            user = users.get(media.id)
            if user is None or user.status is None:
                users.set_status(
                    media.id,
                    TrackingStatus.PLANNED if kind == MediaType.MOVIE
                    else TrackingStatus.WATCHING,
                )

    def close(self) -> None:
        if self._owned_engine is not None:
            self._owned_engine.dispose()
