"""Download and retain artwork for every tracked movie and TV show."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaItem, UserMedia
from izlek.security.token_store import TokenStore
from izlek.services.image_service import ImageService
from izlek.tmdb.client import TmdbClient


class LibraryImagesService:
    """Synchronize library artwork from a background worker, including unseen items."""

    def __init__(
        self, session_factory: sessionmaker[Session] | None = None,
        *, images: ImageService | None = None,
    ) -> None:
        self._factory = session_factory
        self._engine = None
        self._images = images
        self._own_images = images is None
        self._token: str | None = None

    def sync(self) -> dict[str, int]:
        if self._factory is None:
            self._engine = initialize_database()
            self._factory = create_session_factory(self._engine)
        with self._factory() as session:
            artwork = list(session.execute(
                select(MediaItem.poster_path, MediaItem.backdrop_path)
                .join(UserMedia, UserMedia.media_id == MediaItem.id)
                .where(UserMedia.status.is_not(None))
            ))
        if not artwork:
            return {"saved": 0, "unavailable": 0}
        if self._own_images:
            stored = TokenStore().load()
            token = stored.value if stored else None
            if self._images is None or self._token != token:
                if self._images is not None:
                    self._images.close()
                self._images = ImageService(TmdbClient(token=token))
                self._token = token
        result = {"saved": 0, "unavailable": 0}
        seen = set()
        for poster, backdrop in artwork:
            for kind, path in (("poster-detail", poster), ("backdrop", backdrop)):
                if not path or (kind, path) in seen:
                    continue
                seen.add((kind, path))
                # Mark before requesting: maintenance cannot expire a library image.
                self._images.cache.keep(kind, path)
                future = (
                    self._images.poster(path, "detail") if kind == "poster-detail"
                    else self._images.backdrop(path)
                )
                local = future.result()
                saved = local == self._images.cache.path_for(kind, path)
                result["saved" if saved else "unavailable"] += 1
        return result

    def close(self) -> None:
        if self._own_images and self._images is not None:
            self._images.close()
            self._images = None
        if self._engine is not None:
            self._engine.dispose()
