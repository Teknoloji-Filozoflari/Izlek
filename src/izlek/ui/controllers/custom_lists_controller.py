"""Asynchronous QML bridge for local custom lists."""

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.security.token_store import TokenStore
from izlek.services.custom_lists import CustomListsService
from izlek.services.image_service import ImageService
from izlek.tmdb.client import TmdbClient
from izlek.ui.controllers.messages import LOCAL_DATA_UNAVAILABLE


class CustomListsController(QObject):
    """Keep list reads and writes off Qt's UI thread."""

    changed = Signal()
    itemsChanged = Signal()
    _loaded = Signal(int, object, str)
    _poster_ready = Signal(int, str, int, str)

    def __init__(
        self,
        service: CustomListsService | None = None,
        parent: QObject | None = None,
        *,
        images: ImageService | None = None,
        store: TokenStore | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service or CustomListsService()
        self._images = images
        self._own_images = images is None
        self._store = store or TokenStore()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._generation = 0
        self._selected_id = 0
        self._lists: list[dict] = []
        self._items: list[dict] = []
        self._candidates: list[dict] = []
        self._candidate_query = ""
        self._busy = False
        self._error = ""
        self._loaded.connect(self._apply_loaded)
        self._poster_ready.connect(self._apply_poster)

    @Property("QVariantList", notify=changed)
    def lists(self) -> list[dict]:
        return self._lists

    @Property("QVariantList", notify=itemsChanged)
    def items(self) -> list[dict]:
        return self._items

    @Property("QVariantList", notify=changed)
    def candidates(self) -> list[dict]:
        query = self._candidate_query.casefold()
        return [
            item for item in self._candidates
            if query in item["title"].casefold()
        ]

    @Slot(str)
    def searchCandidates(self, query: str) -> None:
        """Filter the loaded local media without network or database work."""
        self._candidate_query = query.strip()
        self.changed.emit()

    @Property(int, notify=changed)
    def selectedId(self) -> int:
        return self._selected_id

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Slot()
    def refresh(self) -> None:
        self._submit(None)

    @Slot(int)
    def selectList(self, list_id: int) -> None:
        self._selected_id = list_id
        self._submit(None)

    def _submit(self, action: Callable[[], int | None] | None) -> None:
        self._generation += 1
        self._busy = True
        self._error = ""
        self.changed.emit()
        self._executor.submit(self._work, self._generation, self._selected_id, action)

    def _work(
        self, generation: int, selected_id: int, action: Callable[[], int | None] | None
    ) -> None:
        try:
            if action is not None:
                new_selection = action()
                if new_selection is not None:
                    selected_id = new_selection
            snapshot = self._service.snapshot(selected_id)
        except (OSError, ValueError, LookupError, SQLAlchemyError):
            self._loaded.emit(generation, {}, LOCAL_DATA_UNAVAILABLE)
        else:
            snapshot["items"] = [{**item, "poster": ""} for item in snapshot["items"]]
            self._loaded.emit(generation, snapshot, "")
            if snapshot["items"]:
                if self._images is None:
                    try:
                        stored = self._store.load()
                    except (OSError, UnicodeError):
                        stored = None
                    self._images = ImageService(
                        TmdbClient(token=stored.value if stored else None)
                    )
                for item in snapshot["items"]:
                    future = self._images.poster(item["poster_path"])
                    future.add_done_callback(
                        lambda done, item=item: self._finish_poster(
                            generation, item, done
                        )
                    )

    def _finish_poster(self, generation: int, item: dict, done: Future) -> None:
        if done.cancelled():
            return
        try:
            url = QUrl.fromLocalFile(str(done.result())).toString()
        except (OSError, ValueError):
            return
        self._poster_ready.emit(generation, item["kind"], item["tmdb_id"], url)

    @Slot(int, str, int, str)
    def _apply_poster(self, generation: int, kind: str, tmdb_id: int, url: str) -> None:
        if generation != self._generation:
            return
        for item in self._items:
            if item["kind"] == kind and item["tmdb_id"] == tmdb_id:
                item["poster"] = url
                self.itemsChanged.emit()
                break

    @Slot()
    def refresh_token(self) -> None:
        self._executor.submit(self._reset_images)
        self.refresh()

    def _reset_images(self) -> None:
        if self._own_images and self._images is not None:
            self._images.close()
            self._images = None

    @Slot(int, object, str)
    def _apply_loaded(self, generation: int, snapshot: dict, error: str) -> None:
        if generation != self._generation:
            return
        self._busy = False
        self._error = error
        if not error:
            self._selected_id = snapshot["selected_id"]
            self._lists = snapshot["lists"]
            self._items = snapshot["items"]
            self._candidates = snapshot["candidates"]
        self.changed.emit()
        self.itemsChanged.emit()

    @Slot(str)
    def createList(self, name: str) -> None:
        self._submit(lambda: self._service.create(name))

    @Slot(int, str)
    def renameList(self, list_id: int, name: str) -> None:
        self._submit(lambda: self._service.rename(list_id, name))

    @Slot(int)
    def deleteList(self, list_id: int) -> None:
        self._submit(lambda: self._service.delete(list_id))

    @Slot(int, str, int)
    def addMedia(self, list_id: int, kind: str, tmdb_id: int) -> None:
        self._submit(lambda: self._service.add(list_id, kind, tmdb_id))

    @Slot(int, str, int)
    def removeMedia(self, list_id: int, kind: str, tmdb_id: int) -> None:
        self._submit(lambda: self._service.remove(list_id, kind, tmdb_id))

    @Slot(int, int)
    def moveList(self, list_id: int, direction: int) -> None:
        self._submit(lambda: self._service.move_list(list_id, direction))

    @Slot(int, str, int, int)
    def moveMedia(self, list_id: int, kind: str, tmdb_id: int, direction: int) -> None:
        self._submit(lambda: self._service.move_item(list_id, kind, tmdb_id, direction))

    def close(self) -> None:
        self._generation += 1
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._reset_images()
        self._service.close()
