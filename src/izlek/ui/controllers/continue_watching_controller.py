"""Nonblocking bridge from local Continue Watching data to the home page."""

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.security.token_store import TokenStore
from izlek.services.continue_watching import ContinueWatchingService
from izlek.services.image_service import ImageService
from izlek.services.tv_detail import TvDetailService
from izlek.tmdb.client import TmdbClient
from izlek.ui.controllers.messages import LOCAL_DATA_UNAVAILABLE


class ContinueWatchingController(QObject):
    """Load cards and save quick actions without blocking Qt's UI thread."""

    changed = Signal()
    _loaded = Signal(int, object, str)
    _image_ready = Signal(int, int, str, str)

    def __init__(
        self,
        service: ContinueWatchingService | None = None,
        tv_service: TvDetailService | None = None,
        images: ImageService | None = None,
        store: TokenStore | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service or ContinueWatchingService()
        self._tv_service = tv_service or TvDetailService(TmdbClient())
        self._store = store or TokenStore()
        self._images = images
        self._own_images = images is None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._generation = 0
        self._future: Future | None = None
        self._image_futures: set[Future] = set()
        self._items: list[dict] = []
        self._busy = False
        self._error = ""
        self._loaded.connect(self._apply_loaded)
        self._image_ready.connect(self._apply_image)

    @Property("QVariantList", notify=changed)
    def items(self) -> list[dict]:
        return self._items

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Slot()
    def refresh_token(self) -> None:
        try:
            stored = self._store.load()
        except (OSError, UnicodeError):
            stored = None
        token = stored.value if stored else None
        self._tv_service.client = TmdbClient(token=token)
        if self._own_images and self._images is not None:
            self._executor.submit(self._images.close)
            self._images = None
        if self._own_images:
            self._images = ImageService(TmdbClient(token=token))

    @Slot()
    def refresh(self) -> None:
        self._generation += 1
        self._cancel_futures()
        generation = self._generation
        self._busy = True
        self._error = ""
        self.changed.emit()
        self._future = self._executor.submit(self._load, generation)

    def _cancel_futures(self) -> None:
        if self._future is not None:
            self._future.cancel()
            self._future = None
        for future in tuple(self._image_futures):
            future.cancel()
        self._image_futures.clear()

    @Slot()
    def cancelPending(self) -> None:
        self._generation += 1
        self._cancel_futures()
        self._busy = False
        self.changed.emit()

    def _load(self, generation: int) -> None:
        try:
            items = [asdict(item) for item in self._service.list_next()]
        except (OSError, ValueError, SQLAlchemyError):
            self._loaded.emit(generation, [], LOCAL_DATA_UNAVAILABLE)
        else:
            self._loaded.emit(generation, items, "")

    @Slot(int, object, str)
    def _apply_loaded(self, generation: int, items: list[dict], error: str) -> None:
        if generation != self._generation:
            return
        if error:
            self._busy = False
            self._error = error
            self.changed.emit()
            return
        self._items = [
            {
                **item,
                "poster": "",
                "backdrop": "",
                "episodeCode": (
                    f"S{item['season_number']:02d}E{item['episode_number']:02d}"
                ),
            }
            for item in items
        ]
        self._busy = False
        self._error = error
        self.changed.emit()
        if self._images is None:
            self.refresh_token()
        assert self._images is not None
        for index, item in enumerate(self._items):
            for role in ("poster", "backdrop"):
                future = (
                    self._images.poster(item["poster_path"])
                    if role == "poster"
                    else self._images.backdrop(item["backdrop_path"])
                )
                self._image_futures.add(future)
                future.add_done_callback(
                    lambda done, i=index, r=role: self._image_done(
                        done, generation, i, r
                    )
                )

    def _image_done(
        self, future: Future, generation: int, index: int, role: str
    ) -> None:
        self._image_futures.discard(future)
        if future.cancelled():
            return
        try:
            path = future.result()
        except (OSError, ValueError):
            return
        self._image_ready.emit(
            generation, index, role, QUrl.fromLocalFile(str(path)).toString()
        )

    @Slot(int, int, str, str)
    def _apply_image(self, generation: int, index: int, role: str, url: str) -> None:
        if generation != self._generation or index >= len(self._items):
            return
        updated = list(self._items)
        updated[index] = {**updated[index], role: url}
        self._items = updated
        self.changed.emit()

    @Slot(int, int, int)
    def markWatched(
        self, tmdb_id: int, season_number: int, episode_number: int
    ) -> None:
        self._generation += 1
        generation = self._generation
        self._busy = True
        self.changed.emit()
        self._future = self._executor.submit(
            self._mark_watched, generation, tmdb_id, season_number, episode_number
        )

    def _mark_watched(
        self, generation: int, tmdb_id: int, season_number: int, episode_number: int
    ) -> None:
        try:
            self._tv_service.set_episode_watched(
                tmdb_id, season_number, episode_number, True
            )
            items = [asdict(item) for item in self._service.list_next()]
        except (OSError, ValueError, LookupError, SQLAlchemyError):
            self._loaded.emit(generation, [], LOCAL_DATA_UNAVAILABLE)
        else:
            self._loaded.emit(generation, items, "")

    def close(self) -> None:
        self.cancelPending()
        self._executor.shutdown(wait=False, cancel_futures=True)
        if self._own_images and self._images is not None:
            self._images.close()
        self._service.close()
        self._tv_service.close()
