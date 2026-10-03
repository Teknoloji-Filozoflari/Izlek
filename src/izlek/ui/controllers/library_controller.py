"""Nonblocking local film and TV library bridge for QML."""

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.db.models import TrackingStatus
from izlek.security.token_store import TokenStore
from izlek.services.favorites import FavoritesService
from izlek.services.image_service import ImageService
from izlek.services.library_common import SORT_OPTIONS, SORT_RECENT
from izlek.services.movie_library import MovieLibraryService
from izlek.services.tv_library import TvLibraryService
from izlek.tmdb.client import TmdbClient
from izlek.ui.controllers.messages import LOCAL_DATA_UNAVAILABLE


class LibraryController(QObject):
    """Keep database reads and poster cache work outside the UI thread."""

    changed = Signal()
    _loaded = Signal(int, object, object, object, str)
    _poster_ready = Signal(int, int, str)
    _favorite_saved = Signal(int, str)

    def __init__(
        self,
        service: MovieLibraryService | TvLibraryService,
        images: ImageService | None = None,
        store: TokenStore | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._images = images
        self._own_images = images is None
        self._store = store or TokenStore()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._generation = 0
        self._status = TrackingStatus.PLANNED
        self._sort_by = SORT_RECENT
        self._items: list[dict] = []
        self._favorites: list[dict] = []
        self._stats: dict[str, int] = {}
        self._poster_paths: dict[int, str] = {}
        self._poster_requested: set[int] = set()
        self._poster_futures: set[Future] = set()
        self._load_future: Future | None = None
        self._poster_flush_scheduled = False
        self._busy = False
        self._error = ""
        self._loaded.connect(self._apply_loaded)
        self._poster_ready.connect(self._apply_poster)
        self._favorite_saved.connect(self._apply_favorite_saved)

    @Property("QVariantList", notify=changed)
    def items(self) -> list[dict]:
        return self._items

    @Property("QVariantList", notify=changed)
    def favorites(self) -> list[dict]:
        return self._favorites

    @Property("QVariantMap", notify=changed)
    def stats(self) -> dict[str, int]:
        return self._stats

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status.value

    @Property(str, notify=changed)
    def sortBy(self) -> str:
        return self._sort_by

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Slot(str)
    def setStatus(self, status: str) -> None:
        if status not in TrackingStatus._value2member_map_ or status == self._status:
            return
        self._status = TrackingStatus(status)
        self.refresh()

    @Slot(str)
    def setSort(self, sort_by: str) -> None:
        if sort_by not in SORT_OPTIONS or sort_by == self._sort_by:
            return
        self._sort_by = sort_by
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        self._generation += 1
        if self._load_future is not None:
            self._load_future.cancel()
        for future in tuple(self._poster_futures):
            future.cancel()
        self._poster_futures.clear()
        self._poster_requested.clear()
        generation = self._generation
        self._busy = True
        self._error = ""
        self.changed.emit()
        self._load_future = self._executor.submit(
            self._load, generation, self._status, self._sort_by
        )

    @Slot(int, bool)
    def setFavorite(self, tmdb_id: int, favorite: bool) -> None:
        """Save a card action in the same local database as this library."""
        self._executor.submit(self._save_favorite, tmdb_id, favorite)

    def _save_favorite(self, tmdb_id: int, favorite: bool) -> None:
        try:
            kind = "movie" if isinstance(self._service, MovieLibraryService) else "tv"
            FavoritesService(self._service._sessions()).set_favorite(
                kind, tmdb_id, favorite
            )
        except (OSError, ValueError, LookupError, SQLAlchemyError):
            self._favorite_saved.emit(tmdb_id, LOCAL_DATA_UNAVAILABLE)
        else:
            self._favorite_saved.emit(tmdb_id, "")

    @Slot(int, str)
    def _apply_favorite_saved(self, tmdb_id: int, error: str) -> None:
        if error:
            self._error = error
            self.changed.emit()
        else:
            self.refresh()

    def _load(self, generation: int, status: TrackingStatus, sort_by: str) -> None:
        try:
            snapshot = self._service.snapshot(status, sort_by)
        except (OSError, ValueError, SQLAlchemyError):
            self._loaded.emit(generation, [], [], {}, LOCAL_DATA_UNAVAILABLE)
        else:
            self._loaded.emit(
                generation,
                [asdict(item) for item in snapshot.items],
                [asdict(item) for item in snapshot.favorites],
                snapshot.stats,
                "",
            )

    @Slot(int, object, object, object, str)
    def _apply_loaded(
        self,
        generation: int,
        items: list[dict],
        favorites: list[dict],
        stats: dict[str, int],
        error: str,
    ) -> None:
        if generation != self._generation:
            return
        self._busy = False
        self._error = error
        if error:
            self.changed.emit()
            return
        self._items = [{**item, "poster": ""} for item in items]
        self._favorites = [{**item, "poster": ""} for item in favorites]
        self._stats = stats
        self._poster_paths = {
            item["tmdb_id"]: item["poster_path"]
            for item in self._items + self._favorites
        }
        self.changed.emit()

    def _reset_images(self) -> None:
        if self._own_images and self._images is not None:
            self._images.close()
            self._images = None
        if self._own_images:
            try:
                stored = self._store.load()
            except (OSError, UnicodeError):
                stored = None
            self._images = ImageService(
                TmdbClient(token=stored.value if stored else None)
            )

    @Slot()
    def refresh_token(self) -> None:
        self._executor.submit(self._reset_images)
        self.refresh()

    @Slot()
    def cancelPending(self) -> None:
        """Cancel queued page work and invalidate late image/database results."""
        self._generation += 1
        if self._load_future is not None:
            self._load_future.cancel()
            self._load_future = None
        for future in tuple(self._poster_futures):
            future.cancel()
        self._poster_futures.clear()
        self._poster_requested.clear()
        self._busy = False
        self.changed.emit()

    @Slot(int)
    def requestPoster(self, tmdb_id: int) -> None:
        """Load only thumbnails requested by instantiated QML delegates."""
        if tmdb_id in self._poster_requested or tmdb_id not in self._poster_paths:
            return
        self._poster_requested.add(tmdb_id)
        generation = self._generation
        if self._images is None:
            self._reset_images()
        assert self._images is not None
        future = self._images.poster(self._poster_paths[tmdb_id])
        self._poster_futures.add(future)

        def finished(done: Future) -> None:
            self._poster_futures.discard(done)
            if done.cancelled():
                return
            try:
                path = done.result()
            except (OSError, ValueError):
                return
            self._poster_ready.emit(
                generation, tmdb_id, QUrl.fromLocalFile(str(path)).toString()
            )

        future.add_done_callback(finished)

    @Slot(int, int, str)
    def _apply_poster(self, generation: int, tmdb_id: int, url: str) -> None:
        if generation != self._generation:
            return
        for item in self._items:
            if item["tmdb_id"] == tmdb_id:
                item["poster"] = url
                break
        for item in self._favorites:
            if item["tmdb_id"] == tmdb_id:
                item["poster"] = url
                break
        if self._poster_flush_scheduled:
            return
        self._poster_flush_scheduled = True
        QTimer.singleShot(16, self._flush_posters)

    @Slot()
    def _flush_posters(self) -> None:
        self._poster_flush_scheduled = False
        self.changed.emit()

    def close(self) -> None:
        self.cancelPending()
        self._executor.shutdown(wait=False, cancel_futures=True)
        if self._own_images and self._images is not None:
            self._images.close()
        self._service.close()
