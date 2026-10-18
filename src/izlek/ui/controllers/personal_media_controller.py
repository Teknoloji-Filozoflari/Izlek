"""Background local review and recommendation preference bridge."""

from concurrent.futures import Future, ThreadPoolExecutor

from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.services.personal_media import PersonalMediaService


class PersonalMediaController(QObject):
    changed = Signal()
    hiddenChanged = Signal()
    recordLoaded = Signal(str, int)
    reviewSaved = Signal(str, int)
    dataChanged = Signal()
    _loaded = Signal(int, object, str)
    _written = Signal(str, str, int, object, str)
    _hidden_ready = Signal(object, str)

    def __init__(
        self, service: PersonalMediaService | None = None, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._service = service or PersonalMediaService()
        self._reads = ThreadPoolExecutor(max_workers=1)
        self._writes = ThreadPoolExecutor(max_workers=1)
        self._future: Future | None = None
        self._generation = 0
        self._identity = ("", 0)
        self._record: dict = {}
        self._hidden: list[dict] = []
        self._saving = False
        self._loading = False
        self._feedback = ""
        self._closed = False
        self._loaded.connect(self._apply_loaded)
        self._written.connect(self._apply_written)
        self._hidden_ready.connect(self._apply_hidden)

    @Property("QVariantMap", notify=changed)
    def current(self) -> dict:
        return self._record

    @Property("QVariantList", notify=hiddenChanged)
    def hiddenItems(self) -> list[dict]:
        return self._hidden

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._loading or self._saving

    @Property(str, notify=changed)
    def feedback(self) -> str:
        return self._feedback

    @Slot(str, int)
    def load(self, kind: str, tmdb_id: int) -> None:
        if self._closed or kind not in ("movie", "tv") or tmdb_id <= 0:
            return
        self._identity = (kind, tmdb_id)
        self._generation += 1
        if self._future:
            self._future.cancel()
        self._record = {}
        self._loading = True
        self._feedback = ""
        self.changed.emit()
        self._future = self._reads.submit(self._read, self._generation, kind, tmdb_id)

    def _read(self, generation: int, kind: str, tmdb_id: int) -> None:
        try:
            record = self._service.read(kind, tmdb_id)
        except (OSError, ValueError, SQLAlchemyError):
            self._loaded.emit(generation, {}, "Kişisel bilgiler okunamadı.")
        else:
            self._loaded.emit(generation, record, "")

    @Slot(int, object, str)
    def _apply_loaded(self, generation: int, record: dict, error: str) -> None:
        if self._closed or generation != self._generation:
            return
        self._record = record
        self._loading = False
        self._feedback = error
        self.changed.emit()
        if record:
            self.recordLoaded.emit(record["kind"], record["id"])

    @Slot(str, int, int, str)
    def saveReview(self, kind: str, tmdb_id: int, rating: int, note: str) -> None:
        if self._closed or self._saving:
            return
        self._invalidate_read(kind, tmdb_id)
        self._saving = True
        self._feedback = ""
        self.changed.emit()
        self._writes.submit(self._write, "review", kind, tmdb_id, (rating, note))

    @Slot("QVariantMap", bool)
    def setDismissed(self, media: dict, dismissed: bool) -> None:
        if self._closed or self._saving:
            return
        try:
            kind, item_id = str(media["mediaType"]), int(media["id"])
        except (KeyError, TypeError, ValueError):
            return
        self._invalidate_read(kind, item_id)
        self._saving = True
        self._feedback = ""
        self.changed.emit()
        self._writes.submit(
            self._write, "dismiss", kind, item_id, (dict(media), dismissed)
        )

    def _invalidate_read(self, kind: str, item_id: int) -> None:
        if self._identity == (kind, item_id):
            self._generation += 1
            self._loading = False
            if self._future is not None:
                self._future.cancel()

    def _write(self, action: str, kind: str, item_id: int, values: tuple) -> None:
        try:
            if action == "review":
                record = self._service.save_review(kind, item_id, *values)
            else:
                self._service.dismiss(*values)
                record = self._service.read(kind, item_id)
        except (OSError, ValueError, LookupError, SQLAlchemyError) as exc:
            message = (
                str(exc)
                if isinstance(exc, (ValueError, LookupError))
                else "Değişiklik kaydedilemedi."
            )
            self._written.emit(action, kind, item_id, {}, message)
        else:
            self._written.emit(action, kind, item_id, record, "")

    @Slot(str, str, int, object, str)
    def _apply_written(
        self, action: str, kind: str, item_id: int, record: dict, error: str
    ) -> None:
        if self._closed:
            return
        self._saving = False
        self._feedback = error or "Kaydedildi."
        if not error and self._identity == (kind, item_id):
            self._record = record
            self.recordLoaded.emit(kind, item_id)
            if action == "review":
                self.reviewSaved.emit(kind, item_id)
        self.changed.emit()
        if not error:
            self.dataChanged.emit()
            self.refreshHidden()

    @Slot()
    def refreshHidden(self) -> None:
        if not self._closed:
            self._reads.submit(self._read_hidden)

    def _read_hidden(self) -> None:
        try:
            items = self._service.hidden()
        except (OSError, ValueError, SQLAlchemyError):
            self._hidden_ready.emit([], "Gizlenen içerikler okunamadı.")
        else:
            self._hidden_ready.emit(items, "")

    @Slot(object, str)
    def _apply_hidden(self, items: list[dict], error: str) -> None:
        if not self._closed:
            if not error:
                self._hidden = items
                self.hiddenChanged.emit()
            else:
                self._feedback = error
                self.changed.emit()

    def close(self) -> None:
        self._closed = True
        self._generation += 1
        self._reads.shutdown(wait=True, cancel_futures=True)
        self._writes.shutdown(wait=True)
        self._service.close()
