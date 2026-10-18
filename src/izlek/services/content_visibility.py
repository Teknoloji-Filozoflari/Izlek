"""Local saved/watched exclusions for remote search results."""

from threading import Lock

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType
from izlek.repositories.local import MediaRepository


class ContentVisibilityService:
    """Read exclusions on workers, scoped by media type and TMDb identity."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._factory = session_factory
        self._engine: Engine | None = None
        self._lock = Lock()

    def excluded_ids(self, kind: str) -> set[int]:
        factory = self._sessions()
        with factory() as session:
            return MediaRepository(session).excluded_tmdb_ids(MediaType(kind.upper()))

    def _sessions(self) -> sessionmaker[Session]:
        with self._lock:
            if self._factory is None:
                self._engine = initialize_database()
                self._factory = create_session_factory(self._engine)
        return self._factory

    def snapshot(self, kind: str) -> dict:
        """Read exclusions and tracking labels together for a person's works."""
        with self._sessions()() as session:
            session.connection().exec_driver_sql("BEGIN")
            repo = MediaRepository(session)
            media_type = MediaType(kind.upper())
            return {
                "excluded": repo.excluded_tmdb_ids(media_type),
                "statuses": {
                    media.tmdb_id: user.status.value if user.status else "SAVED"
                    for media, user in repo.list_local_media(media_type)
                },
            }

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
