"""Asynchronous local favorites bridge for the home page."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.services.favorites import FavoritesService
from izlek.ui.controllers.messages import LOCAL_DATA_UNAVAILABLE


class FavoritesController(QObject):
    """Expose film and TV favorites without database work on the UI thread."""

    changed = Signal()
    _loaded = Signal(int, object, str)

    def __init__(
        self, service: FavoritesService | None = None, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._service = service or FavoritesService()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._generation = 0
        self._items: list[dict] = []
        self._error = ""
        self._loaded.connect(self._apply_loaded)

    @Property("QVariantList", notify=changed)
    def items(self) -> list[dict]:
        return self._items

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Slot()
    def refresh(self) -> None:
        self._generation += 1
        self._executor.submit(self._load, self._generation)

    def _load(self, generation: int) -> None:
        try:
            items = [asdict(item) for item in self._service.list_all()]
        except (OSError, ValueError, SQLAlchemyError):
            self._loaded.emit(generation, [], LOCAL_DATA_UNAVAILABLE)
        else:
            self._loaded.emit(generation, items, "")

    @Slot(int, object, str)
    def _apply_loaded(self, generation: int, items: list[dict], error: str) -> None:
        if generation != self._generation:
            return
        self._error = error
        if not error:
            self._items = items
        self.changed.emit()

    @Slot(str, int, bool)
    def setFavorite(self, kind: str, tmdb_id: int, favorite: bool) -> None:
        self._executor.submit(self._save, kind, tmdb_id, favorite)

    def _save(self, kind: str, tmdb_id: int, favorite: bool) -> None:
        try:
            self._service.set_favorite(kind, tmdb_id, favorite)
        except (OSError, ValueError, LookupError, SQLAlchemyError):
            self._loaded.emit(self._generation, [], LOCAL_DATA_UNAVAILABLE)
        else:
            self._load(self._generation)

    def close(self) -> None:
        self._generation += 1
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._service.close()
