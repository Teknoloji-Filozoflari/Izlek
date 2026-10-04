"""Nonblocking local statistics bridge for QML."""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.security.token_store import TokenStore
from izlek.services.image_service import ImageService
from izlek.services.statistics import StatisticsService
from izlek.tmdb.client import TmdbClient
from izlek.ui.controllers.messages import LOCAL_DATA_UNAVAILABLE


class StatisticsController(QObject):
    """Expose a local statistics snapshot without blocking Qt's UI thread."""

    changed = Signal()
    _loaded = Signal(int, object, str)
    _poster_ready = Signal(int, int, str)

    def __init__(
        self,
        service: StatisticsService | None = None,
        parent: QObject | None = None,
        *,
        images: ImageService | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service or StatisticsService()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._generation = 0
        self._stats: dict = {}
        self._busy = False
        self._error = ""
        self._images = images
        self._own_images = images is None
        self._loaded.connect(self._apply_loaded)
        self._poster_ready.connect(self._apply_poster)

    @Property("QVariantMap", notify=changed)
    def stats(self) -> dict:
        return self._stats

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Slot()
    def refresh(self) -> None:
        self._generation += 1
        generation = self._generation
        self._busy = True
        self._error = ""
        self.changed.emit()
        self._executor.submit(self._load, generation)

    def _load(self, generation: int) -> None:
        try:
            stats = self._service.snapshot().as_dict()
        except (OSError, ValueError, SQLAlchemyError):
            self._loaded.emit(generation, {}, LOCAL_DATA_UNAVAILABLE)
        else:
            self._loaded.emit(generation, stats, "")
            if self._images is None and stats.get("top_shows"):
                self._reset_images()
            for item in stats.get("top_shows", []):
                future = self._images.poster(item["posterPath"])
                future.add_done_callback(
                    lambda done, item_id=item["id"]: self._poster_finished(
                        done, generation, item_id
                    )
                )

    def _reset_images(self) -> None:
        if not self._own_images:
            return
        if self._images is not None:
            self._images.close()
        try:
            stored = TokenStore().load()
        except (OSError, UnicodeError):
            stored = None
        self._images = ImageService(TmdbClient(token=stored.value if stored else None))

    @Slot()
    def refresh_token(self) -> None:
        self._executor.submit(self._reset_images)
        self.refresh()

    def _poster_finished(
        self, future: Future[Path], generation: int, item_id: int
    ) -> None:
        if future.cancelled():
            return
        try:
            path = future.result()
        except (OSError, ValueError):
            return
        self._poster_ready.emit(
            generation, item_id, QUrl.fromLocalFile(str(path)).toString()
        )

    @Slot(int, int, str)
    def _apply_poster(self, generation: int, item_id: int, url: str) -> None:
        if generation != self._generation:
            return
        self._stats = {
            **self._stats,
            "top_shows": [
                {**item, "poster": url} if item["id"] == item_id else item
                for item in self._stats.get("top_shows", [])
            ],
        }
        self.changed.emit()

    @Slot(int, object, str)
    def _apply_loaded(self, generation: int, stats: dict, error: str) -> None:
        if generation != self._generation:
            return
        self._busy = False
        self._error = error
        if not error:
            self._stats = stats
        self.changed.emit()

    def close(self) -> None:
        self._generation += 1
        self._executor.shutdown(wait=True, cancel_futures=True)
        if self._own_images and self._images is not None:
            self._images.close()
        self._service.close()
