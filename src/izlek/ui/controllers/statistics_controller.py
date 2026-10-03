"""Nonblocking local statistics bridge for QML."""

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.services.statistics import StatisticsService
from izlek.ui.controllers.messages import LOCAL_DATA_UNAVAILABLE


class StatisticsController(QObject):
    """Expose a local statistics snapshot without blocking Qt's UI thread."""

    changed = Signal()
    _loaded = Signal(int, object, str)

    def __init__(
        self,
        service: StatisticsService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service or StatisticsService()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._generation = 0
        self._stats: dict = {}
        self._busy = False
        self._error = ""
        self._loaded.connect(self._apply_loaded)

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
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._service.close()
