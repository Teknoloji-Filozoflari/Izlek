"""Global TMDb search and detail state exposed to QML."""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.i18n import t
from izlek.security.token_store import TokenStore
from izlek.services.content_visibility import ContentVisibilityService
from izlek.services.director_search import DirectorSearchService
from izlek.services.image_service import ImageService
from izlek.tmdb.client import NetworkError, TmdbClient, TMDbError
from izlek.tmdb.models import MovieSummary, TvSummary
from izlek.ui.controllers.messages import local_data_unavailable, network_unavailable


def _local_url(path: Path) -> str:
    return QUrl.fromLocalFile(str(path)).toString()


class SearchController(QObject):
    """Run searches off the UI thread and discard stale responses."""

    resultsChanged = Signal()
    stateChanged = Signal()
    detailChanged = Signal()
    mediaTypeChanged = Signal()
    _searchFinished = Signal(int, str, object, str)
    _posterReady = Signal(int, str, int, str)
    _detailFinished = Signal(int, object, str)
    _detailPosterReady = Signal(int, str)
    _visibilityReady = Signal(int, object, object, str)
    _directorsReady = Signal(int, object, str)

    def __init__(
        self,
        store: TokenStore | None = None,
        client: TmdbClient | None = None,
        images: ImageService | None = None,
        executor: ThreadPoolExecutor | None = None,
        parent: QObject | None = None,
        visibility: ContentVisibilityService | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store or TokenStore()
        self._visibility = visibility or ContentVisibilityService()
        self._excluded: dict[str, set[int]] = {}
        self._closed = False
        self._client = client
        self._images = images
        self._retired_images: list[ImageService] = []
        self._executor = executor or ThreadPoolExecutor(max_workers=3)
        self._own_executor = executor is None
        self._own_images = images is None
        self._generation = 0
        self._detail_generation = 0
        self._futures: list[Future[Any]] = []
        self._movies: list[dict[str, Any]] = []
        self._shows: list[dict[str, Any]] = []
        self._directors: list[dict] = []
        self._director: dict = {}
        self._person_role = "director"
        self._person_kind = ""
        self._person_items: list[dict] = []
        self._include_saved = False
        self._local_statuses: dict[str, dict[int, str]] = {}
        self._pending: set[str] = set()
        self._errors: dict[str, str] = {}
        self._error = ""
        self._busy = False
        self._media_type = "all"
        self._detail: dict[str, Any] = {}
        self._detail_busy = False
        self._detail_error = ""
        self._searchFinished.connect(self._apply_search)
        self._posterReady.connect(self._apply_poster)
        self._detailFinished.connect(self._apply_detail)
        self._detailPosterReady.connect(self._apply_detail_poster)
        self._visibilityReady.connect(self._apply_visibility)
        self._directorsReady.connect(self._apply_directors)
        if client is None:
            self.refresh_token()

    @Property("QVariantList", notify=resultsChanged)
    def movies(self) -> list[dict[str, Any]]:
        return self._movies

    @Property("QVariantList", notify=resultsChanged)
    def shows(self) -> list[dict[str, Any]]:
        return self._shows

    @Property("QVariantList", notify=resultsChanged)
    def directors(self) -> list[dict]:
        return self._directors

    @Property("QVariantMap", notify=resultsChanged)
    def selectedDirector(self) -> dict:
        return self._director

    @Property("QVariantList", notify=resultsChanged)
    def people(self) -> list[dict]:
        return self._directors

    @Property("QVariantMap", notify=resultsChanged)
    def selectedPerson(self) -> dict:
        return self._director

    @Property(bool, notify=resultsChanged)
    def includeSaved(self) -> bool:
        return self._include_saved

    @Slot(bool)
    def setIncludeSaved(self, include: bool) -> None:
        """Change only person results; retain the complete fetched filmography."""
        if self._closed or not self._director or include == self._include_saved:
            return
        self._include_saved = include
        self._publish_person_items()

    def _publish_person_items(self) -> None:
        items = [item for item in self._person_items
                 if self._include_saved or not item.get("saved")]
        self._movies = items if self._person_kind == "movie" else []
        self._shows = items if self._person_kind == "tv" else []
        self.resultsChanged.emit()

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=mediaTypeChanged)
    def mediaType(self) -> str:
        return self._media_type

    @Slot(str)
    def setMediaType(self, kind: str) -> None:
        """Select search endpoints and invalidate previous category results."""
        if kind not in ("all", "movie", "tv") or kind == self._media_type:
            return
        self._media_type = kind
        self.clear()
        self.mediaTypeChanged.emit()

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
            self._retired_images.append(old_images)
            self._executor.submit(old_images.close)
            self._images = None
        self.clear()
        self._client = TmdbClient(token=stored.value) if stored else None

    @Slot(str)
    def search(self, query: str) -> None:
        """Start movie and TV searches for a debounced query."""
        if self._closed:
            return
        self._generation += 1
        for future in self._futures:
            future.cancel()
        self._futures.clear()
        self._movies = []
        self._shows = []
        self._directors = []
        self._director = {}
        self._person_items = []
        self._person_kind = ""
        self._include_saved = False
        self._local_statuses = {}
        self._errors = {}
        self._excluded = {}
        self._error = ""
        self._pending = set()
        self._busy = False
        self.resultsChanged.emit()
        self.stateChanged.emit()
        query = query.strip()
        if len(query) < 3:
            return
        if self._client is None:
            self._error = t("errors.token_missing")
            self.stateChanged.emit()
            return
        if self._images is None:
            self._images = ImageService(self._client)
        client = self._client
        images = self._images
        kinds = ("movie", "tv") if self._media_type == "all" else (self._media_type,)
        self._pending = set(kinds)
        self._busy = True
        self.stateChanged.emit()
        for kind in kinds:
            future = self._executor.submit(
                self._search_one, self._generation, kind, query, client, images
            )
            self._futures.append(future)

    @Slot(str)
    def searchDirectors(self, query: str) -> None:
        """Resolve names on a worker before requesting directing credits."""
        self.searchPeople(query, "director")

    @Slot(str, str)
    def searchPeople(self, query: str, role: str) -> None:
        """Search acting or directing names without changing title-search rules."""
        if role not in ("actor", "director"):
            return
        if self._closed:
            return
        self.search("")
        self._person_role = role
        if len(query.strip()) < 3:
            return
        if self._client is None:
            self._error = t("errors.token_missing")
            self.stateChanged.emit()
            return
        self._pending = {"person"}
        self._busy = True
        self.stateChanged.emit()
        self._futures.append(self._executor.submit(
            self._find_directors, self._generation, query.strip(), self._client, role
        ))

    def _find_directors(
        self, generation: int, query: str, client: TmdbClient, role: str = "director"
    ) -> None:
        try:
            people = DirectorSearchService(client).search(query, role)
        except NetworkError:
            self._directorsReady.emit(generation, [], network_unavailable())
        except (TMDbError, OSError, ValueError):
            self._directorsReady.emit(
                generation, [], "Kişi araması tamamlanamadı. Tekrar deneyin."
            )
        else:
            self._directorsReady.emit(generation, people, "")

    @Slot(int, object, str)
    def _apply_directors(self, generation: int, people: list[dict], error: str) -> None:
        if self._closed or generation != self._generation:
            return
        self._directors = people
        self._pending.clear()
        self._busy = False
        self._error = error
        self.resultsChanged.emit()
        self.stateChanged.emit()

    @Slot(int, str)
    def selectDirector(self, person_id: int, kind: str) -> None:
        self.selectPerson(person_id, kind, "director")

    @Slot(int, str, str)
    def selectPerson(self, person_id: int, kind: str, role: str) -> None:
        if role not in ("actor", "director"):
            return
        if self._closed or kind not in ("movie", "tv") or self._client is None:
            return
        person = next((row for row in self._directors if row["id"] == person_id), None)
        if person is None:
            return
        people = self._directors
        include_saved = (self._include_saved if self._director == person
                         and self._person_role == role else False)
        self.search("")
        self._directors = people
        self._director = person
        self._person_role = role
        self._person_kind = kind
        self._include_saved = include_saved
        if self._images is None:
            self._images = ImageService(self._client)
        self._pending = {kind}
        self._busy = True
        self.resultsChanged.emit()
        self.stateChanged.emit()
        self._futures.append(self._executor.submit(
            self._directed_works, self._generation, person_id, kind,
            self._client, self._images, role
        ))

    @Slot(int, str, str)
    def openActor(self, person_id: int, name: str, kind: str) -> None:
        """Open an exact cast identity without a name lookup or ambiguous match."""
        if (self._closed or person_id <= 0 or not name.strip()
                or kind not in ("movie", "tv")):
            return
        self.search("")
        if self._client is None:
            self._error = t("errors.token_missing")
            self.stateChanged.emit()
            return
        self._directors = [{"id": person_id, "name": name.strip()}]
        self.selectPerson(person_id, kind, "actor")

    def _directed_works(
        self, generation: int, person_id: int, kind: str,
        client: TmdbClient, images: ImageService, role: str = "director",
    ) -> None:
        try:
            works = DirectorSearchService(client).works(person_id, kind, role)
            local = self._visibility.snapshot(kind)
            items = [{
                **self._summary(item, kind, images), "score": item.vote_average,
                "saved": item.id in local["excluded"],
                "status": local["statuses"].get(
                    item.id, "SAVED" if item.id in local["excluded"] else ""
                ),
            } for item in works]
        except NetworkError:
            self._searchFinished.emit(generation, kind, [], network_unavailable())
        except TMDbError:
            self._searchFinished.emit(
                generation, kind, [],
                "Kişinin yapımları yüklenemedi. Tekrar deneyin."
            )
        except (OSError, ValueError, SQLAlchemyError):
            self._searchFinished.emit(generation, kind, [], local_data_unavailable())
        else:
            self._searchFinished.emit(generation, kind, items, "")

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
            excluded = self._visibility.excluded_ids(kind)
            items = [self._summary(item, kind, images) for item in page.results
                     if item.id not in excluded]
        except NetworkError:
            self._searchFinished.emit(
                generation,
                kind,
                [],
                network_unavailable(),
            )
        except TMDbError:
            self._searchFinished.emit(
                generation, kind, [], "TMDb araması tamamlanamadı. Tekrar deneyin."
            )
        except (OSError, ValueError, SQLAlchemyError):
            self._searchFinished.emit(generation, kind, [], local_data_unavailable())
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
            "releaseDate": date or "",
            "posterPath": item.poster_path or "",
            "poster": _local_url(images.poster(None).result()),
        }

    @Slot(int, str, object, str)
    def _apply_search(
        self, generation: int, kind: str, items: list[dict[str, Any]], error: str
    ) -> None:
        if generation != self._generation:
            return
        person_results = bool(self._director) and kind == self._person_kind
        if person_results:
            if kind in self._excluded:
                items = self._update_person_states(items, kind)
            self._person_items = items
            self._publish_person_items()
        else:
            items = [item for item in items
                     if item["id"] not in self._excluded.get(kind, set())]
        if not person_results:
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

    @Slot()
    def refresh_visibility(self) -> None:
        """Hide newly saved results without repeating the remote search."""
        if not self._closed:
            self._executor.submit(
                self._read_visibility, self._generation, bool(self._director)
            )

    def _read_visibility(self, generation: int, person_results: bool = False) -> None:
        statuses = {}
        try:
            if person_results:
                snapshots = {kind: self._visibility.snapshot(kind)
                             for kind in ("movie", "tv")}
                excluded = {kind: snapshot["excluded"]
                            for kind, snapshot in snapshots.items()}
                statuses = {kind: snapshot["statuses"]
                            for kind, snapshot in snapshots.items()}
            else:
                excluded = {kind: self._visibility.excluded_ids(kind)
                            for kind in ("movie", "tv")}
        except (OSError, ValueError, SQLAlchemyError):
            self._visibilityReady.emit(generation, {}, {}, local_data_unavailable())
        else:
            self._visibilityReady.emit(generation, excluded, statuses, "")

    @Slot(int, object, object, str)
    def _apply_visibility(
        self, generation: int, excluded: dict, statuses: dict, error: str
    ) -> None:
        if self._closed or generation != self._generation:
            return
        if error:
            self._error = error
            self.stateChanged.emit()
            return
        self._excluded = excluded
        self._local_statuses = statuses
        if self._director:
            self._person_items = self._update_person_states(
                self._person_items, self._person_kind
            )
            self._publish_person_items()
            return
        self._movies = [item for item in self._movies
                        if item["id"] not in excluded["movie"]]
        self._shows = [item for item in self._shows
                       if item["id"] not in excluded["tv"]]
        self.resultsChanged.emit()

    def _update_person_states(self, items: list[dict], kind: str) -> list[dict]:
        excluded = self._excluded.get(kind, set())
        statuses = self._local_statuses.get(kind, {})
        return [{**item, "saved": item["id"] in excluded,
                 "status": statuses.get(
                     item["id"], "SAVED" if item["id"] in excluded else ""
                 )} for item in items]

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
        if self._director and kind == self._person_kind:
            self._person_items = [
                {**item, "poster": url} if item["id"] == item_id else item
                for item in self._person_items
            ]
            self._publish_person_items()
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
                generation, {}, network_unavailable()
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
        self._closed = True
        self._generation += 1
        self._detail_generation += 1
        for future in self._futures:
            future.cancel()
        self._futures.clear()
        if self._own_executor:
            self._executor.shutdown(wait=True, cancel_futures=True)
        if self._own_images and self._images is not None:
            self._images.close()
        for images in self._retired_images:
            images.close()
        self._retired_images.clear()
        self._visibility.close()
