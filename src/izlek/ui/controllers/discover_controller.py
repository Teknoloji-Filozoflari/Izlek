"""Filtered TMDb Discover results for the desktop exploration page."""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from izlek.security.token_store import TokenStore
from izlek.services.image_service import ImageService
from izlek.tmdb.client import NetworkError, TmdbClient, TMDbError
from izlek.tmdb.models import MovieSummary, TvSummary
from izlek.ui.controllers.messages import NETWORK_UNAVAILABLE

_MIN_VOTE_COUNT = 100


def _local_url(path: Path) -> str:
    return QUrl.fromLocalFile(str(path)).toString()


class DiscoverController(QObject):
    """Load controlled, score-ranked Discover pages outside the UI thread."""

    changed = Signal()
    _loaded = Signal(int, object, int, int, str)
    _poster_ready = Signal(int, int, str)

    def __init__(
        self,
        store: TokenStore | None = None,
        client: TmdbClient | None = None,
        images: ImageService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store or TokenStore()
        self._client = client
        self._images = images
        self._own_images = images is None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._future: Future | None = None
        self._image_futures: set[Future] = set()
        self._generation = 0
        self._items: list[dict[str, Any]] = []
        self._kind = "movie"
        self._year = 0
        self._genre_id = 0
        self._country = ""
        self._min_score = 0
        self._max_score = 100
        self._page = 1
        self._total_pages = 1
        self._busy = False
        self._error = ""
        self._loaded.connect(self._apply_loaded)
        self._poster_ready.connect(self._apply_poster)
        if client is None:
            self.refresh_token()

    @Property("QVariantList", notify=changed)
    def items(self) -> list[dict[str, Any]]:
        return self._items

    @Property(str, notify=changed)
    def mediaKind(self) -> str:
        return self._kind

    @Property(int, notify=changed)
    def page(self) -> int:
        return self._page

    @Property(int, notify=changed)
    def totalPages(self) -> int:
        return self._total_pages

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Slot()
    def refresh_token(self) -> None:
        """Use a recently stored TMDb token for later Discover requests."""
        try:
            stored = self._store.load()
        except (OSError, UnicodeError):
            stored = None
        if self._own_images and self._images is not None:
            old_images = self._images
            self._executor.submit(old_images.close)
            self._images = None
        self._client = TmdbClient(token=stored.value) if stored else None

    @Slot(str, str, int, str, int, int)
    def applyFilters(
        self,
        kind: str,
        year: str,
        genre_id: int,
        country: str,
        min_score: int,
        max_score: int,
    ) -> None:
        """Replace filters and return to the first controlled results page."""
        if kind not in {"movie", "tv"}:
            return
        try:
            parsed_year = int(year) if year.strip() else 0
        except ValueError:
            return
        if parsed_year and not 1888 <= parsed_year <= 2100:
            return
        self._kind = kind
        self._year = parsed_year
        self._genre_id = max(0, genre_id)
        self._country = country.strip().upper()
        self._min_score = max(0, min(min_score, 100))
        self._max_score = max(self._min_score, min(max_score, 100))
        self._load(1)

    @Slot(int)
    def goToPage(self, page: int) -> None:
        """Load one explicit page instead of automatically scrolling forever."""
        if self._busy:
            return
        self._load(max(1, min(page, self._total_pages)))

    def _load(self, page: int) -> None:
        self._generation += 1
        if self._future is not None:
            self._future.cancel()
        for future in tuple(self._image_futures):
            future.cancel()
        self._image_futures.clear()
        generation = self._generation
        self._page = page
        self._items = []
        self._error = ""
        self._busy = True
        self.changed.emit()
        if self._client is None:
            self._busy = False
            self._error = "TMDb tokenı bulunamadı. Ayarlar'dan token ekleyin."
            self.changed.emit()
            return
        if self._images is None:
            self._images = ImageService(self._client)
        self._future = self._executor.submit(
            self._request_page,
            generation,
            self._client,
            self._images,
            self._kind,
            page,
            self._year,
            self._genre_id,
            self._country,
            self._min_score,
            self._max_score,
        )

    @Slot()
    def cancelPending(self) -> None:
        """Invalidate a Discover request after leaving the page."""
        self._generation += 1
        if self._future is not None:
            self._future.cancel()
            self._future = None
        for future in tuple(self._image_futures):
            future.cancel()
        self._image_futures.clear()
        self._busy = False
        self.changed.emit()

    def _request_page(
        self,
        generation: int,
        client: TmdbClient,
        images: ImageService,
        kind: str,
        page: int,
        year: int,
        genre_id: int,
        country: str,
        min_score: int,
        max_score: int,
    ) -> None:
        try:
            result = (
                client.discover_movie(
                    page=page,
                    year=year or None,
                    genre_id=genre_id or None,
                    country=country,
                    min_score=min_score / 10,
                    max_score=max_score / 10,
                    min_vote_count=_MIN_VOTE_COUNT,
                )
                if kind == "movie"
                else client.discover_tv(
                    page=page,
                    year=year or None,
                    genre_id=genre_id or None,
                    country=country,
                    min_score=min_score / 10,
                    max_score=max_score / 10,
                    min_vote_count=_MIN_VOTE_COUNT,
                )
            )
            items = [self._summary(item, kind, images) for item in result.results]
        except NetworkError:
            self._loaded.emit(generation, [], page, 1, NETWORK_UNAVAILABLE)
        except TMDbError:
            self._loaded.emit(
                generation, [], page, 1, "Keşfet sonuçları yüklenemedi. Tekrar deneyin."
            )
        else:
            self._loaded.emit(generation, items, result.page, result.total_pages, "")

    @staticmethod
    def _summary(
        item: MovieSummary | TvSummary, kind: str, images: ImageService
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
            "progressText": f"TMDb {item.vote_average:.1f}",
        }

    @Slot(int, object, int, int, str)
    def _apply_loaded(
        self,
        generation: int,
        items: list[dict[str, Any]],
        page: int,
        total_pages: int,
        error: str,
    ) -> None:
        if generation != self._generation:
            return
        self._busy = False
        self._error = error
        self._page = page
        self._total_pages = max(1, total_pages)
        self._items = items
        self.changed.emit()
        if error:
            return
        assert self._images is not None
        for item in items:
            future = self._images.poster(item["posterPath"])
            self._image_futures.add(future)
            future.add_done_callback(
                lambda done, item_id=item["id"], generation=generation:
                self._poster_done(done, generation, item_id)
            )

    def _poster_done(self, future: Future, generation: int, item_id: int) -> None:
        self._image_futures.discard(future)
        if future.cancelled():
            return
        try:
            url = _local_url(future.result())
        except (OSError, ValueError):
            return
        self._poster_ready.emit(generation, item_id, url)

    @Slot(int, int, str)
    def _apply_poster(self, generation: int, item_id: int, url: str) -> None:
        if generation != self._generation:
            return
        for index, item in enumerate(self._items):
            if item["id"] == item_id:
                self._items[index] = {**item, "poster": url}
                self.changed.emit()
                return

    def close(self) -> None:
        self.cancelPending()
        self._executor.shutdown(wait=False, cancel_futures=True)
        if self._own_images and self._images is not None:
            self._images.close()
