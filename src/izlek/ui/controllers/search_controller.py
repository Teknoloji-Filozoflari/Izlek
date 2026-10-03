"""Global TMDb search and detail state exposed to QML."""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from izlek.security.token_store import TokenStore
from izlek.services.image_service import ImageService
from izlek.tmdb.client import NetworkError, TmdbClient, TMDbError
from izlek.tmdb.models import MovieSummary, TvSummary
from izlek.ui.controllers.messages import NETWORK_UNAVAILABLE


def _local_url(path: Path) -> str:
    return QUrl.fromLocalFile(str(path)).toString()


class SearchController(QObject):
    """Run searches off the UI thread and discard stale responses."""

    resultsChanged = Signal()
    stateChanged = Signal()
    detailChanged = Signal()
    _searchFinished = Signal(int, str, object, str)
    _posterReady = Signal(int, str, int, str)
    _detailFinished = Signal(int, object, str)
    _detailPosterReady = Signal(int, str)

    def __init__(
        self,
        store: TokenStore | None = None,
        client: TmdbClient | None = None,
        images: ImageService | None = None,
        executor: ThreadPoolExecutor | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store or TokenStore()
        self._client = client
        self._images = images
        self._executor = executor or ThreadPoolExecutor(max_workers=3)
        self._own_executor = executor is None
        self._own_images = images is None
        self._generation = 0
        self._detail_generation = 0
        self._futures: list[Future[Any]] = []
        self._movies: list[dict[str, Any]] = []
        self._shows: list[dict[str, Any]] = []
        self._pending: set[str] = set()
        self._errors: dict[str, str] = {}
        self._error = ""
        self._busy = False
        self._detail: dict[str, Any] = {}
        self._detail_busy = False
        self._detail_error = ""
        self._searchFinished.connect(self._apply_search)
        self._posterReady.connect(self._apply_poster)
        self._detailFinished.connect(self._apply_detail)
        self._detailPosterReady.connect(self._apply_detail_poster)
        if client is None:
            self.refresh_token()

    @Property("QVariantList", notify=resultsChanged)
    def movies(self) -> list[dict[str, Any]]:
        return self._movies

    @Property("QVariantList", notify=resultsChanged)
    def shows(self) -> list[dict[str, Any]]:
        return self._shows

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=stateChanged)
    def error(self) -> str:
        return self._error

    @Property("QVariantMap", notify=detailChanged)
    def detail(self) -> dict[str, Any]:
        return self._detail

    @Property(bool, notify=detailChanged)
    def detailBusy(self) -> bool:
        return self._detail_busy

    @Property(str, notify=detailChanged)
    def detailError(self) -> str:
        return self._detail_error

    @Slot()
    def refresh_token(self) -> None:
        """Refresh credentials after onboarding or token replacement."""
        try:
            stored = self._store.load()
        except (OSError, UnicodeError):
            stored = None
        if self._own_images and self._images is not None:
            old_images = self._images
            self._executor.submit(old_images.close)
            self._images = None
        self.clear()
        self._client = TmdbClient(token=stored.value) if stored else None

    @Slot(str)
    def search(self, query: str) -> None:
        """Start movie and TV searches for a debounced query."""
        self._generation += 1
        for future in self._futures:
            future.cancel()
        self._futures.clear()
        self._movies = []
        self._shows = []
        self._errors = {}
        self._error = ""
        self._pending = set()
        self._busy = False
        self.resultsChanged.emit()
        self.stateChanged.emit()
        query = query.strip()
        if len(query) < 3:
            return
        if self._client is None:
            self._error = "TMDb tokenı bulunamadı. Ayarlar'dan token ekleyin."
            self.stateChanged.emit()
            return
        if self._images is None:
            self._images = ImageService(self._client)
        client = self._client
        images = self._images
        self._pending = {"movie", "tv"}
        self._busy = True
        self.stateChanged.emit()
        for kind in ("movie", "tv"):
            future = self._executor.submit(
                self._search_one, self._generation, kind, query, client, images
            )
            self._futures.append(future)

    @Slot()
    def clear(self) -> None:
        """Invalidate requests when the overlay closes."""
        self._detail_generation += 1
        self._detail_busy = False
        self.detailChanged.emit()
        self.search("")

    def _search_one(
        self,
        generation: int,
        kind: str,
        query: str,
        client: TmdbClient,
        images: ImageService,
    ) -> None:
        try:
            page = (
                client.search_movie(query)
                if kind == "movie"
                else client.search_tv(query)
            )
            items = [self._summary(item, kind, images) for item in page.results]
        except NetworkError:
            self._searchFinished.emit(
                generation,
                kind,
                [],
                NETWORK_UNAVAILABLE,
            )
        except TMDbError:
            self._searchFinished.emit(
                generation, kind, [], "TMDb araması tamamlanamadı. Tekrar deneyin."
            )
        else:
            self._searchFinished.emit(generation, kind, items, "")

    def _summary(
        self, item: MovieSummary | TvSummary, kind: str, images: ImageService
    ) -> dict[str, Any]:
        title = item.original_title if kind == "movie" else item.original_name
        date = item.release_date if kind == "movie" else item.first_air_date
        return {
            "id": item.id,
            "mediaType": kind,
            "title": title,
            "year": date[:4] if date else "",
            "posterPath": item.poster_path or "",
            "poster": _local_url(images.poster(None).result()),
        }

    @Slot(int, str, object, str)
    def _apply_search(
        self, generation: int, kind: str, items: list[dict[str, Any]], error: str
    ) -> None:
        if generation != self._generation:
            return
        if kind == "movie":
            self._movies = items
        else:
            self._shows = items
        self._errors[kind] = error
        self._pending.discard(kind)
        self._busy = bool(self._pending)
        if not self._busy:
            self._error = next(
                (message for message in self._errors.values() if message), ""
            )
        self.resultsChanged.emit()
        self.stateChanged.emit()
        assert self._images is not None
        for item in items:
            future = self._images.poster(item["posterPath"])
            self._futures.append(future)
            future.add_done_callback(
                lambda done, item=item, kind=kind, generation=generation:
                self._poster_finished(done, generation, kind, item["id"])
            )

    def _poster_finished(
        self, future: Future, generation: int, kind: str, item_id: int
    ) -> None:
        if future.cancelled():
            return
        try:
            url = _local_url(future.result())
        except (OSError, ValueError):
            return
        self._posterReady.emit(generation, kind, item_id, url)

    @Slot(int, str, int, str)
    def _apply_poster(self, generation: int, kind: str, item_id: int, url: str) -> None:
        if generation != self._generation:
            return
        source = self._movies if kind == "movie" else self._shows
        for index, item in enumerate(source):
            if item["id"] == item_id:
                source[index] = {**item, "poster": url}
                self.resultsChanged.emit()
                break

    @Slot(str, int)
    def loadDetail(self, kind: str, item_id: int) -> None:
        """Load metadata for the selected search result."""
        self._detail_generation += 1
        generation = self._detail_generation
        self._detail = {}
        self._detail_error = ""
        self._detail_busy = True
        self.detailChanged.emit()
        if self._client is None or kind not in ("movie", "tv"):
            self._detail_busy = False
            self._detail_error = "Detay yüklenemedi."
            self.detailChanged.emit()
            return
        if self._images is None:
            self._images = ImageService(self._client)
        future = self._executor.submit(
            self._load_detail,
            generation,
            kind,
            item_id,
            self._client,
            self._images,
        )
        self._futures.append(future)

    def _load_detail(
        self,
        generation: int,
        kind: str,
        item_id: int,
        client: TmdbClient,
        images: ImageService,
    ) -> None:
        try:
            item = (
                client.movie(item_id)
                if kind == "movie"
                else client.tv(item_id)
            )
            date = item.release_date if kind == "movie" else item.first_air_date
            detail = {
                "id": item.id,
                "mediaType": kind,
                "title": item.original_title if kind == "movie" else item.original_name,
                "year": date[:4] if date else "",
                "overview": item.overview,
                "posterPath": item.poster_path or "",
                "poster": _local_url(images.poster(None).result()),
            }
        except NetworkError:
            self._detailFinished.emit(
                generation, {}, NETWORK_UNAVAILABLE
            )
        except TMDbError:
            self._detailFinished.emit(generation, {}, "Medya detayı yüklenemedi.")
        else:
            self._detailFinished.emit(generation, detail, "")

    @Slot(int, object, str)
    def _apply_detail(
        self, generation: int, detail: dict[str, Any], error: str
    ) -> None:
        if generation != self._detail_generation:
            return
        self._detail = detail
        self._detail_error = error
        self._detail_busy = False
        self.detailChanged.emit()
        if detail and self._images is not None:
            future = self._images.poster(detail["posterPath"], "detail")
            self._futures.append(future)
            future.add_done_callback(
                lambda done: self._detail_poster_finished(done, generation)
            )

    def _detail_poster_finished(self, future: Future, generation: int) -> None:
        if future.cancelled():
            return
        try:
            url = _local_url(future.result())
        except (OSError, ValueError):
            return
        self._detailPosterReady.emit(generation, url)

    @Slot(int, str)
    def _apply_detail_poster(self, generation: int, url: str) -> None:
        if generation == self._detail_generation:
            self._detail = {**self._detail, "poster": url}
            self.detailChanged.emit()

    def close(self) -> None:
        """Release background resources at application shutdown."""
        self._generation += 1
        self._detail_generation += 1
        for future in self._futures:
            future.cancel()
        self._futures.clear()
        if self._own_executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
        if self._own_images and self._images is not None:
            self._images.close()
