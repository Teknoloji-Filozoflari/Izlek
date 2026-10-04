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
    itemsChanged = Signal()
    imageAvailable = Signal(int, str, str)
    progressSaved = Signal()
    _loaded = Signal(int, object, str)
    _progress_saved = Signal(int)
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
        self._retired_images: list[ImageService] = []
        self._own_images = images is None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._generation = 0
        self._future: Future | None = None
        self._write_future: Future | None = None
        self._closed = False
        self._image_futures: set[Future] = set()
        self._items: list[dict] = []
        self._image_urls: dict[tuple[int, str, str], str] = {}
        self._busy = False
        self._error = ""
        self._loaded.connect(self._apply_loaded)
        self._progress_saved.connect(self._apply_progress_saved)
        self._image_ready.connect(self._apply_image)

    @Property("QVariantList", notify=itemsChanged)
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
        self._executor.submit(self._reset_images)

    def _reset_images(self) -> None:
        """Read keyring and initialize HTTP clients only on the worker thread."""
        try:
            stored = self._store.load()
        except (OSError, UnicodeError):
            stored = None
        token = stored.value if stored else None
        self._tv_service.client = TmdbClient(token=token)
        if self._own_images and self._images is not None:
            self._retired_images.append(self._images)
            self._images.close()
            self._images = None
        if self._own_images:
            self._images = ImageService(TmdbClient(token=token))

    @Slot()
    def refresh(self) -> None:
        if self._closed:
            return
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
            if items and self._images is None:
                self._reset_images()
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
            self._items = []
            self.itemsChanged.emit()
            self.changed.emit()
            return
        next_items = [
            {
                **item,
                "poster": self._image_urls.get(
                    (item["tmdb_id"], "poster", item["poster_path"]), ""
                ),
                "backdrop": self._image_urls.get(
                    (item["tmdb_id"], "backdrop", item["backdrop_path"]), ""
                ),
                "episodeCode": (
                    f"S{item['season_number']:02d}E{item['episode_number']:02d}"
                ),
            }
            for item in items
        ]
        model_changed = next_items != self._items
        self._items = next_items
        self._busy = False
        self._error = error
        self.changed.emit()
        if model_changed:
            self.itemsChanged.emit()
        if not self._items:
            return
        assert self._images is not None
        for index, item in enumerate(self._items):
            for role in ("poster", "backdrop"):
                if item[role]:
                    continue
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
        item = updated[index]
        if not url.endswith("-placeholder.svg"):
            self._image_urls[(item["tmdb_id"], role, item[role + "_path"])] = url
        updated[index] = {**updated[index], role: url}
        self._items = updated
        self.imageAvailable.emit(item["tmdb_id"], role, url)

    @Slot(int, int, int)
    def markWatched(
        self, tmdb_id: int, season_number: int, episode_number: int
    ) -> None:
        if self._closed or self._busy or (
            self._write_future is not None and not self._write_future.done()
        ):
            return
        if not any(
            (item["tmdb_id"], item["season_number"], item["episode_number"])
            == (tmdb_id, season_number, episode_number)
            for item in self._items
        ):
            return
        self._generation += 1
        self._cancel_futures()
        generation = self._generation
        self._busy = True
        self._error = ""
        self.changed.emit()
        self._write_future = self._executor.submit(
            self._mark_watched, generation, tmdb_id, season_number, episode_number
        )

    def _mark_watched(
        self, generation: int, tmdb_id: int, season_number: int, episode_number: int
    ) -> None:
        try:
            self._tv_service.set_episode_watched(
                tmdb_id, season_number, episode_number, True, require_in_library=True
            )
            items = [asdict(item) for item in self._service.list_next()]
        except LookupError:
            self._load(generation)
        except (OSError, ValueError, SQLAlchemyError):
            self._loaded.emit(generation, [], LOCAL_DATA_UNAVAILABLE)
        else:
            self._loaded.emit(generation, items, "")
            self._progress_saved.emit(generation)

    @Slot(int)
    def _apply_progress_saved(self, generation: int) -> None:
        if not self._closed:
            self.progressSaved.emit()

    def close(self) -> None:
        self._closed = True
        self.cancelPending()
        self._executor.shutdown(wait=True, cancel_futures=True)
        if self._own_images and self._images is not None:
            self._images.close()
        for images in self._retired_images:
            images.close()
        self._retired_images.clear()
        self._service.close()
        self._tv_service.close()
