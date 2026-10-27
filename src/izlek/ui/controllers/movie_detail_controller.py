"""Nonblocking movie detail and local tracking state for QML."""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from sqlalchemy.exc import SQLAlchemyError

from izlek.i18n import t
from izlek.metadata.registry import MetadataClientRegistry
from izlek.metadata.settings import MetadataSettings
from izlek.security.token_store import TokenStore
from izlek.services.image_service import ImageService
from izlek.services.movie_detail import MovieDetailService
from izlek.tmdb.client import NetworkError, TmdbClient, TMDbError
from izlek.ui.controllers.messages import network_unavailable


def _url(path: Path) -> str:
    return QUrl.fromLocalFile(str(path)).toString()


class MovieDetailController(QObject):
    """Load remote sections and persist actions without blocking QML."""

    changed = Signal()
    libraryChanged = Signal()
    _loaded = Signal(int, object, str)
    _saved = Signal(int, object, str)
    _imageReady = Signal(int, str, int, str)

    def __init__(
        self,
        service: MovieDetailService | None = None,
        images: ImageService | None = None,
        store: TokenStore | None = None,
        metadata_settings: MetadataSettings | None = None,
        metadata_registry: MetadataClientRegistry | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store or TokenStore()
        self._metadata_settings = metadata_settings or MetadataSettings()
        self._metadata_registry = metadata_registry
        self._service = service or MovieDetailService(
            TmdbClient(),
            watch_region=lambda: self._metadata_settings.watch_provider_region,
            metadata_registry=self._metadata_registry,
        )
        self._images = images
        self._retired_images: list[ImageService] = []
        self._own_images = images is None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._write_executor = ThreadPoolExecutor(max_workers=1)
        self._closed = False
        self._futures: set[Future] = set()
        self._generation = 0
        self._detail: dict[str, Any] = {}
        self._busy = False
        self._saving = False
        self._error = ""
        self._feedback = ""
        self._image_notify_pending = False
        self._pending_images: dict[tuple[str, int], str] = {}
        self._loaded.connect(self._apply_loaded)
        self._saved.connect(self._apply_saved)
        self._imageReady.connect(self._apply_image)
        if service is None:
            self.refresh_token()

    @Property("QVariantMap", notify=changed)
    def detail(self) -> dict[str, Any]:
        return self._detail

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=changed)
    def saving(self) -> bool:
        return self._saving

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Property(str, notify=changed)
    def feedback(self) -> str:
        return self._feedback

    @Slot()
    def refresh_token(self) -> None:
        """Use a newly saved token for later metadata requests."""
        try:
            stored = self._store.load()
        except (OSError, UnicodeError):
            stored = None
        if self._own_images and self._images is not None:
            old_images = self._images
            self._retired_images.append(old_images)
            # Resource cleanup must survive page-request cancellation.
            self._executor.submit(old_images.close)
            self._images = None
        self._service.client = TmdbClient(token=stored.value if stored else None)

    @Slot(int)
    def loadMovie(self, movie_id: int) -> None:
        """Fetch the chosen movie and its persisted state."""
        self._cancel_futures()
        self._generation += 1
        generation = self._generation
        self._detail = {}
        self._busy = True
        self._saving = False
        self._error = ""
        self._feedback = ""
        self.changed.emit()
        self._submit(self._load, generation, movie_id)

    def _submit(self, function, *args) -> Future:
        future = self._executor.submit(function, *args)
        self._futures.add(future)
        future.add_done_callback(self._futures.discard)
        return future

    def _cancel_futures(self) -> None:
        for future in tuple(self._futures):
            future.cancel()
        self._futures.clear()

    @Slot()
    def cancelPending(self) -> None:
        """Invalidate page work and cancel tasks that have not started."""
        self._generation += 1
        self._cancel_futures()
        self._busy = False
        self._saving = False
        self.changed.emit()

    def _load(self, generation: int, movie_id: int) -> None:
        try:
            cached = self._service.cached(movie_id)
        except (OSError, ValueError, KeyError, SQLAlchemyError):
            cached = None
        if cached is not None:
            self._loaded.emit(generation, cached, "")
        try:
            if cached is not None and not self._service.needs_refresh(movie_id):
                return
            detail = self._service.load(movie_id)
        except NetworkError:
            if cached is None:
                self._loaded.emit(
                    generation,
                    {},
                    network_unavailable(),
                )
        except (TMDbError, OSError, ValueError, KeyError, SQLAlchemyError):
            if cached is None:
                self._loaded.emit(generation, {}, "Film bilgisi yüklenemedi.")
        else:
            if detail != cached:
                self._loaded.emit(generation, detail, "")

    @Slot(int, object, str)
    def _apply_loaded(
        self, generation: int, detail: dict[str, Any], error: str
    ) -> None:
        if generation != self._generation:
            return
        self._busy = False
        self._error = error
        self._image_notify_pending = False
        self._pending_images.clear()
        if not detail:
            self._detail = detail
            self.changed.emit()
            return
        if self._images is None:
            self._images = ImageService(self._service.client)
        placeholder = _url(self._images.poster(None).result())
        backdrop_placeholder = _url(self._images.backdrop(None).result())
        # Single notify (like TV detail): avoid a double full-page rebind on open.
        self._detail = {
            **detail,
            "poster": placeholder,
            "backdrop": backdrop_placeholder,
            "cast": [{**item, "poster": ""} for item in detail.get("cast", [])],
            "similar": [{**item, "poster": placeholder} for item in detail["similar"]],
            "recommendations": [
                {**item, "poster": placeholder} for item in detail["recommendations"]
            ],
        }
        self.changed.emit()
        self._schedule_image(
            generation,
            "poster",
            -1,
            self._images.poster(detail["posterPath"], "detail"),
        )
        self._schedule_image(
            generation, "backdrop", -1, self._images.backdrop(detail["backdropPath"])
        )
        for index, item in enumerate(detail.get("cast", [])):
            self._schedule_image(
                generation, "cast", index,
                self._images.profile(item.get("profilePath")),
            )
        for role in ("recommendations",):
            for index, item in enumerate(detail[role]):
                self._schedule_image(
                    generation, role, index, self._images.poster(item["posterPath"])
                )

    def _schedule_image(self, generation: int, role: str, index: int, future) -> None:
        self._futures.add(future)

        def finished(done: Future) -> None:
            self._futures.discard(done)
            if done.cancelled():
                return
            try:
                url = _url(done.result())
            except (OSError, ValueError):
                return
            self._imageReady.emit(generation, role, index, url)

        future.add_done_callback(finished)

    def _flush_image_notify(self) -> None:
        self._image_notify_pending = False
        if self._closed or not self._pending_images:
            self._pending_images.clear()
            return
        detail = dict(self._detail)
        by_role: dict[str, dict[int, str]] = {}
        for (role, index), url in self._pending_images.items():
            by_role.setdefault(role, {})[index] = url
        self._pending_images.clear()
        for role, updates in by_role.items():
            entries = list(detail.get(role, []))
            for index, url in updates.items():
                if index < len(entries):
                    entries[index] = {**entries[index], "poster": url}
            detail[role] = entries
        self._detail = detail
        self.changed.emit()

    @Slot(int, str, int, str)
    def _apply_image(self, generation: int, role: str, index: int, url: str) -> None:
        if generation != self._generation:
            return
        if role in ("poster", "backdrop"):
            self._detail = {**self._detail, role: url}
            # Hero media updates immediately; secondary images are coalesced below.
            self.changed.emit()
            return
        # Buffer until flush so Property/QML stay in sync (tests wait on detail).
        self._pending_images[(role, index)] = url
        if not self._image_notify_pending:
            self._image_notify_pending = True
            QTimer.singleShot(0, self._flush_image_notify)

    @Slot(str)
    def setStatus(self, status: str) -> None:
        if status not in ("PLANNED", "WATCHING", "WATCHED"):
            return
        self._submit_action("status", status)

    @Slot(bool)
    def setFavorite(self, favorite: bool) -> None:
        self._submit_action("favorite", favorite)

    @Slot()
    def removeFromLibrary(self) -> None:
        self._submit_action("status", None)

    @Slot(str)
    def addToList(self, name: str) -> None:
        self._submit_action("list", name)

    @Slot()
    def addCollectionToList(self) -> None:
        """Import the TMDb collection/franchise into a local custom list."""
        if not (self._detail.get("collectionId") or 0):
            return
        self._submit_action("collection", None)

    def _submit_action(self, action: str, value: Any) -> None:
        if self._closed or not self._detail or self._saving:
            return
        self._saving = True
        self._feedback = ""
        self.changed.emit()
        generation = self._generation
        movie_id = self._detail["id"]
        # Navigation cancels reads, but an accepted personal edit must persist.
        self._write_executor.submit(self._save, generation, movie_id, action, value)

    def _save(self, generation: int, movie_id: int, action: str, value: Any) -> None:
        try:
            if action == "status":
                detail = self._service.set_status(movie_id, value)
                feedback = t("detail.saved")
            elif action == "favorite":
                detail = self._service.set_favorite(movie_id, value)
                feedback = t("detail.saved")
            elif action == "collection":
                detail, info = self._service.add_collection_to_list(movie_id)
                feedback = t(
                    "detail.collection_added",
                    name=info["listName"],
                    added=info["added"],
                    total=info["total"],
                )
            else:
                detail = self._service.add_to_list(movie_id, value)
                feedback = t("detail.saved")
        except NetworkError:
            self._saved.emit(generation, {}, network_unavailable())
        except (TMDbError, OSError, ValueError, LookupError, KeyError, SQLAlchemyError):
            self._saved.emit(
                generation,
                {},
                t("detail.collection_failed")
                if action == "collection"
                else "Değişiklik kaydedilemedi.",
            )
        else:
            self._saved.emit(generation, detail, feedback)

    @Slot(int, object, str)
    def _apply_saved(
        self, generation: int, detail: dict[str, Any], feedback: str
    ) -> None:
        if self._closed:
            return
        if generation != self._generation:
            if detail:
                self.libraryChanged.emit()
            return
        self._saving = False
        if detail:
            self._detail = {
                **detail,
                "poster": self._detail.get("poster", ""),
                "backdrop": self._detail.get("backdrop", ""),
                "similar": self._detail.get("similar", []),
                "cast": self._detail.get("cast", []),
                "recommendations": self._detail.get("recommendations", []),
            }
        self._feedback = feedback
        self.changed.emit()
        if detail:
            self.libraryChanged.emit()

    @Slot()
    def openTrailer(self) -> None:
        """Open only the validated YouTube trailer URL in the system browser."""
        url = self._detail.get("trailerUrl", "")
        if url.startswith("https://www.youtube.com/watch?v="):
            QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def openProviderLink(self) -> None:
        """Open only TMDb's provider link returned for the configured region."""
        url = self._detail.get("providerLink", "")
        if url.startswith("https://www.themoviedb.org/"):
            QDesktopServices.openUrl(QUrl(url))

    def close(self) -> None:
        """Release worker, image, and database resources."""
        self._closed = True
        self._generation += 1
        self._cancel_futures()
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._write_executor.shutdown(wait=True)
        if self._own_images and self._images is not None:
            self._images.close()
        for images in self._retired_images:
            images.close()
        self._retired_images.clear()
        self._service.close()
