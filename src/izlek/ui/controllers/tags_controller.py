"""Asynchronous QML bridge for local media tags."""

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.services.tags import TagsService


class TagsController(QObject):
    """Keep tag catalog and per-media edits off the UI thread."""

    changed = Signal()
    mediaTagsChanged = Signal(str, int)
    dataChanged = Signal()
    _catalog_ready = Signal(object, str)
    _media_ready = Signal(int, str, int, object, str)
    _written = Signal(str, str, int, object, str)

    def __init__(
        self,
        service: TagsService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service or TagsService()
        self._reads = ThreadPoolExecutor(max_workers=1)
        self._writes = ThreadPoolExecutor(max_workers=1)
        self._generation = 0
        self._identity = ("", 0)
        self._tags: list[dict] = []
        self._current: list[str] = []
        self._busy = False
        self._feedback = ""
        self._closed = False
        self._catalog_ready.connect(self._apply_catalog)
        self._media_ready.connect(self._apply_media)
        self._written.connect(self._apply_written)

    @Property("QVariantList", notify=changed)
    def tags(self) -> list[dict]:
        return self._tags

    @Property("QVariantList", notify=changed)
    def current(self) -> list[str]:
        return self._current

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=changed)
    def feedback(self) -> str:
        return self._feedback

    @Slot()
    def refresh(self) -> None:
        if not self._closed:
            self._reads.submit(self._load_catalog)

    def _load_catalog(self) -> None:
        try:
            items = self._service.list_all()
        except (OSError, ValueError, SQLAlchemyError):
            self._catalog_ready.emit([], "Etiketler okunamadı.")
        else:
            self._catalog_ready.emit(items, "")

    @Slot(object, str)
    def _apply_catalog(self, items: list[dict], error: str) -> None:
        if self._closed:
            return
        if not error:
            self._tags = items
        self._feedback = error
        self.changed.emit()

    @Slot(str, int)
    def loadForMedia(self, kind: str, tmdb_id: int) -> None:
        if self._closed or kind not in ("movie", "tv") or tmdb_id <= 0:
            return
        self._identity = (kind, tmdb_id)
        self._generation += 1
        generation = self._generation
        self._busy = True
        self._feedback = ""
        self.changed.emit()
        self._reads.submit(self._read_media, generation, kind, tmdb_id)

    def _read_media(self, generation: int, kind: str, tmdb_id: int) -> None:
        try:
            names = self._service.names_for(kind, tmdb_id)
        except (OSError, ValueError, SQLAlchemyError):
            self._media_ready.emit(
                generation, kind, tmdb_id, [], "Etiketler okunamadı."
            )
        else:
            self._media_ready.emit(generation, kind, tmdb_id, names, "")

    @Slot(int, str, int, object, str)
    def _apply_media(
        self, generation: int, kind: str, tmdb_id: int, names: list[str], error: str
    ) -> None:
        if self._closed or generation != self._generation:
            return
        self._busy = False
        self._feedback = error
        if not error and self._identity == (kind, tmdb_id):
            self._current = names
        self.changed.emit()
        if not error:
            self.mediaTagsChanged.emit(kind, tmdb_id)

    @Slot(str, int, str)
    def addTag(self, kind: str, tmdb_id: int, name: str) -> None:
        self._mutate("add", kind, tmdb_id, name)

    @Slot(str, int, str)
    def removeTag(self, kind: str, tmdb_id: int, name: str) -> None:
        self._mutate("remove", kind, tmdb_id, name)

    @Slot(str)
    def createTag(self, name: str) -> None:
        if self._closed or self._busy:
            return
        self._busy = True
        self._feedback = ""
        self.changed.emit()
        self._writes.submit(self._create_tag, name)

    def _create_tag(self, name: str) -> None:
        try:
            self._service.create(name)
            catalog = self._service.list_all()
        except (OSError, ValueError, LookupError, SQLAlchemyError) as exc:
            message = (
                str(exc)
                if isinstance(exc, (ValueError, LookupError))
                else "Etiket oluşturulamadı."
            )
            self._written.emit("create", "", 0, [], message)
        else:
            self._written.emit("create", "", 0, catalog, "")

    def _mutate(self, action: str, kind: str, tmdb_id: int, name: str) -> None:
        if self._closed or self._busy or kind not in ("movie", "tv") or tmdb_id <= 0:
            return
        self._busy = True
        self._feedback = ""
        self.changed.emit()
        self._writes.submit(self._write, action, kind, tmdb_id, name)

    def _write(self, action: str, kind: str, tmdb_id: int, name: str) -> None:
        try:
            if action == "add":
                names = self._service.add_to_media(kind, tmdb_id, name)
            else:
                names = self._service.remove_from_media(kind, tmdb_id, name)
            catalog = self._service.list_all()
        except (OSError, ValueError, LookupError, SQLAlchemyError) as exc:
            message = (
                str(exc)
                if isinstance(exc, (ValueError, LookupError))
                else "Etiket kaydedilemedi."
            )
            self._written.emit(action, kind, tmdb_id, {}, message)
        else:
            payload = {"names": names, "catalog": catalog}
            self._written.emit(action, kind, tmdb_id, payload, "")

    @Slot(str, str, int, object, str)
    def _apply_written(
        self, action: str, kind: str, item_id: int, payload: object, error: str
    ) -> None:
        if self._closed:
            return
        self._busy = False
        self._feedback = error or ("Kaydedildi." if action != "create" else "")
        if not error:
            if action == "create":
                self._tags = list(payload) if isinstance(payload, list) else []
            elif isinstance(payload, dict):
                self._tags = list(payload.get("catalog") or [])
                if self._identity == (kind, item_id):
                    self._current = list(payload.get("names") or [])
                    self.mediaTagsChanged.emit(kind, item_id)
            self.dataChanged.emit()
        self.changed.emit()
        if not error and action == "create":
            self.refresh()

    def close(self) -> None:
        self._closed = True
        self._generation += 1
        self._reads.shutdown(wait=True, cancel_futures=True)
        self._writes.shutdown(wait=True)
        self._service.close()
