"""Background, duplicate-safe quick additions from home result cards."""

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.services.quick_library import QuickLibraryService


class QuickLibraryController(QObject):
    changed = Signal()
    libraryAdded = Signal()
    _loaded = Signal(object, str, str)

    def __init__(
        self, service: QuickLibraryService | None = None, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._service = service or QuickLibraryService()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._states: dict[str, str] = {}
        self._pending: set[str] = set()
        self._error = ""
        self._closed = False
        self._loaded.connect(self._apply_loaded)

    @Property("QVariantMap", notify=changed)
    def states(self) -> dict[str, str]:
        return {**self._states, **dict.fromkeys(self._pending, "adding")}

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Slot()
    def refresh(self) -> None:
        if not self._closed:
            self._executor.submit(self._work, None, "")

    @Slot("QVariantMap")
    def add(self, summary: dict) -> None:
        if self._closed:
            return
        kind, item_id = summary.get("mediaType"), summary.get("id")
        if kind not in ("movie", "tv") or not isinstance(item_id, int) or item_id <= 0:
            return
        key = f"{kind}:{item_id}"
        if key in self._pending or key in self._states:
            return
        self._pending.add(key)
        self._error = ""
        self.changed.emit()
        self._executor.submit(self._work, dict(summary), key)

    def _work(self, summary: dict | None, key: str) -> None:
        try:
            if summary is not None:
                self._service.add(summary)
            states = self._service.states()
        except (OSError, ValueError, KeyError, TypeError, SQLAlchemyError):
            self._loaded.emit({}, key, "Kütüphane güncellenemedi. Tekrar deneyin.")
        else:
            self._loaded.emit(states, key, "")

    @Slot(object, str, str)
    def _apply_loaded(self, states: dict, key: str, error: str) -> None:
        if self._closed:
            return
        self._pending.discard(key)
        self._error = error
        if not error:
            self._states = states
        self.changed.emit()
        if key and not error:
            self.libraryAdded.emit()

    def close(self) -> None:
        self._closed = True
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._service.close()
