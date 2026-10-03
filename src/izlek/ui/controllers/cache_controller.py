"""Background bridge for the disposable image cache in Settings."""

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Property, QObject, Signal, Slot

from izlek.cache.images import ImageDiskCache
from izlek.ui.controllers.messages import FILE_OPERATION_FAILED


def format_bytes(value: int) -> str:
    """Format cache size for a compact Turkish UI label."""
    if value < 1024:
        return f"{value} B"
    units = ("KB", "MB", "GB")
    size = float(value)
    for unit in units:
        size /= 1024
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
    return "0 B"


class CacheController(QObject):
    """Measure and clear image cache without blocking the Qt thread."""

    changed = Signal()
    _finished = Signal(int, str, int, str)

    def __init__(self, cache: ImageDiskCache | None = None, parent=None) -> None:
        super().__init__(parent)
        self._cache = cache or ImageDiskCache()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._generation = 0
        self._busy = False
        self._size = 0
        self._feedback = ""
        self._feedback_kind = "neutral"
        self._finished.connect(self._apply_finished)
        self.refresh()

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=changed)
    def sizeLabel(self) -> str:
        return format_bytes(self._size)

    @Property(int, notify=changed)
    def sizeBytes(self) -> int:
        return self._size

    @Property(str, notify=changed)
    def feedback(self) -> str:
        return self._feedback

    @Property(str, notify=changed)
    def feedbackKind(self) -> str:
        return self._feedback_kind

    @Slot()
    def refresh(self) -> None:
        self._submit("size")

    @Slot()
    def clear(self) -> None:
        self._submit("clear")

    def _submit(self, action: str) -> None:
        if self._busy:
            return
        self._generation += 1
        generation = self._generation
        self._busy = True
        self._feedback = ""
        self.changed.emit()
        self._executor.submit(self._work, generation, action)

    def _work(self, generation: int, action: str) -> None:
        try:
            if action == "clear":
                removed = self._cache.clear()
                size = self._cache.size_bytes()
            else:
                removed = 0
                size = self._cache.size_bytes()
        except OSError:
            self._finished.emit(generation, action, 0, "ERROR:" + FILE_OPERATION_FAILED)
        else:
            self._finished.emit(generation, action, size, str(removed))

    @Slot(int, str, int, str)
    def _apply_finished(
        self, generation: int, action: str, size: int, detail: str
    ) -> None:
        if generation != self._generation:
            return
        self._busy = False
        self._size = size
        if detail.startswith("ERROR:"):
            self._feedback = detail.removeprefix("ERROR:") or "Cache işlemi başarısız."
            self._feedback_kind = "danger"
        elif action == "clear":
            self._feedback = f"Cache temizlendi ({detail} dosya)."
            self._feedback_kind = "success"
        else:
            self._feedback = ""
        self.changed.emit()

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
