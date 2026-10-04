"""Nonblocking TV detail and episode progress bridge for QML."""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from sqlalchemy.exc import SQLAlchemyError

from izlek.security.token_store import TokenStore
from izlek.services.image_service import ImageService
from izlek.services.tv_detail import TvDetailService
from izlek.tmdb.client import NetworkError, TmdbClient, TMDbError
from izlek.ui.controllers.messages import NETWORK_UNAVAILABLE


def _url(path: Path) -> str:
    return QUrl.fromLocalFile(str(path)).toString()


class TvDetailController(QObject):
    """Expose TV detail and local progress while keeping I/O off the UI thread."""

    changed = Signal()
    libraryChanged = Signal()
    _loaded = Signal(int, object, str)
    _seasonLoaded = Signal(int, int, object, str)
    _saved = Signal(int, object, object, str)
    _imageReady = Signal(int, int, str, int, str)

    def __init__(
        self,
        service: TvDetailService | None = None,
        images: ImageService | None = None,
        store: TokenStore | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store or TokenStore()
        self._service = service or TvDetailService(TmdbClient())
        self._images = images
        self._retired_images: list[ImageService] = []
        self._own_images = images is None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._futures: set[Future] = set()
        self._generation = 0
        self._season_generation = 0
        self._detail: dict[str, Any] = {}
        self._episodes: list[dict[str, Any]] = []
        self._selected_season = -1
        self._busy = False
        self._season_busy = False
        self._saving = False
        self._error = ""
        self._season_error = ""
        self._feedback = ""
        self._loaded.connect(self._apply_loaded)
        self._seasonLoaded.connect(self._apply_season)
        self._saved.connect(self._apply_saved)
        self._imageReady.connect(self._apply_image)
        if service is None:
            self.refresh_token()

    @Property("QVariantMap", notify=changed)
    def detail(self) -> dict[str, Any]:
        return self._detail

    @Property("QVariantList", notify=changed)
    def episodes(self) -> list[dict[str, Any]]:
        return self._episodes

    @Property(int, notify=changed)
    def selectedSeason(self) -> int:
        return self._selected_season

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=changed)
    def seasonBusy(self) -> bool:
        return self._season_busy

    @Property(bool, notify=changed)
    def saving(self) -> bool:
        return self._saving

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Property(str, notify=changed)
    def seasonError(self) -> str:
        return self._season_error

    @Property(str, notify=changed)
    def feedback(self) -> str:
        return self._feedback

    @Slot()
    def refresh_token(self) -> None:
        try:
            stored = self._store.load()
        except (OSError, UnicodeError):
            stored = None
        if self._own_images and self._images is not None:
            old = self._images
            self._retired_images.append(old)
            self._submit_future(old.close)
            self._images = None
        self._service.client = TmdbClient(token=stored.value if stored else None)

    @Slot(int)
    def loadTv(self, tv_id: int) -> None:
        self._cancel_futures()
        self._generation += 1
        generation = self._generation
        self._season_generation += 1
        self._detail = {}
        self._episodes = []
        self._selected_season = -1
        self._busy = True
        self._season_busy = False
        self._saving = False
        self._error = ""
        self._feedback = ""
        self.changed.emit()
        self._submit_future(self._load, generation, tv_id)

    def _submit_future(self, function, *args) -> Future:
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
        """Invalidate detail/season work when its page is no longer visible."""
        self._generation += 1
        self._season_generation += 1
        self._cancel_futures()
        self._busy = False
        self._season_busy = False
        self._saving = False
        self.changed.emit()

    def _load(self, generation: int, tv_id: int) -> None:
        try:
            cached = self._service.cached(tv_id)
        except (OSError, ValueError, LookupError, KeyError, SQLAlchemyError):
            cached = None
        if cached is not None:
            self._loaded.emit(generation, cached, "")
        try:
            if cached is not None and not self._service.needs_refresh(tv_id):
                return
            detail = self._service.load(tv_id)
        except NetworkError:
            if cached is None:
                self._loaded.emit(
                    generation,
                    {},
                    NETWORK_UNAVAILABLE,
                )
        except (TMDbError, OSError, ValueError, LookupError, KeyError, SQLAlchemyError):
            if cached is None:
                self._loaded.emit(generation, {}, "Dizi bilgisi yüklenemedi.")
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
        self._detail = detail
        if detail:
            if self._images is None:
                self._images = ImageService(self._service.client)
            poster = _url(self._images.poster(None).result())
            backdrop = _url(self._images.backdrop(None).result())
            self._detail = {
                **detail,
                "poster": poster,
                "backdrop": backdrop,
                "cast": [{**item, "poster": ""} for item in detail.get("cast", [])],
                "similar": [{**item, "poster": poster} for item in detail["similar"]],
                "recommendations": [
                    {**item, "poster": poster} for item in detail["recommendations"]
                ],
            }
            self._schedule_image(
                generation,
                -1,
                "poster",
                -1,
                self._images.poster(detail["posterPath"], "detail"),
            )
            self._schedule_image(
                generation,
                -1,
                "backdrop",
                -1,
                self._images.backdrop(detail["backdropPath"]),
            )
            for index, item in enumerate(detail.get("cast", [])):
                self._schedule_image(
                    generation, -1, "cast", index,
                    self._images.profile(item.get("profilePath")),
                )
            for role in ("recommendations",):
                for index, item in enumerate(detail[role]):
                    self._schedule_image(
                        generation,
                        -1,
                        role,
                        index,
                        self._images.poster(item["posterPath"]),
                    )
        self.changed.emit()
        if detail and detail["seasons"]:
            if any(
                item["number"] == self._selected_season for item in detail["seasons"]
            ):
                return
            regular = next(
                (item for item in detail["seasons"] if item["number"] > 0),
                detail["seasons"][0],
            )
            self.selectSeason(regular["number"])

    @Slot(int)
    def selectSeason(self, season_number: int) -> None:
        if (
            self._saving
            or not self._detail
            or not any(
                item["number"] == season_number for item in self._detail["seasons"]
            )
        ):
            return
        self._season_generation += 1
        serial = self._season_generation
        self._selected_season = season_number
        self._episodes = []
        self._season_busy = True
        self._season_error = ""
        self.changed.emit()
        self._submit_future(
            self._load_season,
            self._generation,
            serial,
            self._detail["id"],
            season_number,
        )

    def _load_season(
        self, generation: int, serial: int, tv_id: int, season_number: int
    ) -> None:
        try:
            cached = self._service.cached_season(tv_id, season_number)
            detail = self._service.cached(tv_id) or {}
        except (OSError, ValueError, LookupError, KeyError, SQLAlchemyError):
            cached = None
            detail = {}
        cached_published = False
        try:
            if cached is not None and self._service.has_cached_season(
                tv_id, season_number
            ):
                self._seasonLoaded.emit(
                    generation,
                    serial,
                    {"episodes": cached, "detail": detail},
                    "",
                )
                cached_published = True
                if not self._service.season_needs_refresh(tv_id, season_number):
                    return
            else:
                cached = None
            episodes = self._service.load_season(tv_id, season_number)
            detail = self._service.cached(tv_id) or {}
        except NetworkError:
            if not cached_published:
                self._seasonLoaded.emit(
                    generation,
                    serial,
                    {},
                    NETWORK_UNAVAILABLE,
                )
        except (TMDbError, OSError, ValueError, LookupError, KeyError, SQLAlchemyError):
            if not cached_published:
                self._seasonLoaded.emit(generation, serial, {}, "Sezon yüklenemedi.")
        else:
            if episodes != cached:
                self._seasonLoaded.emit(
                    generation,
                    serial,
                    {"episodes": episodes, "detail": detail},
                    "",
                )

    @Slot(int, int, object, str)
    def _apply_season(
        self, generation: int, serial: int, payload: dict[str, Any], error: str
    ) -> None:
        if generation != self._generation or serial != self._season_generation:
            return
        self._season_busy = False
        self._season_error = error
        detail = payload.get("detail")
        if detail:
            self._detail = {
                **detail,
                "poster": self._detail.get("poster", ""),
                "backdrop": self._detail.get("backdrop", ""),
                "similar": self._detail.get("similar", []),
                "cast": self._detail.get("cast", []),
                "recommendations": self._detail.get("recommendations", []),
            }
        self._set_episodes(payload.get("episodes", []))

    def _set_episodes(self, episodes: list[dict[str, Any]]) -> None:
        if self._images is None:
            self._episodes = episodes
            self.changed.emit()
            return
        placeholder = _url(self._images.still(None).result())
        self._episodes = [{**item, "still": placeholder} for item in episodes]
        self.changed.emit()
        for index, item in enumerate(episodes):
            self._schedule_image(
                self._generation,
                self._season_generation,
                "still",
                index,
                self._images.still(item["stillPath"]),
            )

    def _schedule_image(
        self,
        generation: int,
        season_generation: int,
        role: str,
        index: int,
        future: Future[Path],
    ) -> None:
        self._futures.add(future)

        def finished(done: Future[Path]) -> None:
            self._futures.discard(done)
            if done.cancelled():
                return
            try:
                url = _url(done.result())
            except (OSError, ValueError):
                return
            self._imageReady.emit(generation, season_generation, role, index, url)

        future.add_done_callback(finished)

    @Slot(int, int, str, int, str)
    def _apply_image(
        self, generation: int, season_generation: int, role: str, index: int, url: str
    ) -> None:
        if generation != self._generation:
            return
        if role == "still":
            if season_generation != self._season_generation or index >= len(
                self._episodes
            ):
                return
            entries = list(self._episodes)
            entries[index] = {**entries[index], "still": url}
            self._episodes = entries
        elif role in ("poster", "backdrop"):
            self._detail = {**self._detail, role: url}
        else:
            entries = list(self._detail.get(role, []))
            if index >= len(entries):
                return
            entries[index] = {**entries[index], "poster": url}
            self._detail = {**self._detail, role: entries}
        self.changed.emit()

    @Slot(int, bool)
    def setEpisodeWatched(self, episode_number: int, watched: bool) -> None:
        self._submit("episode", episode_number, watched)

    @Slot(bool)
    def setSeasonWatched(self, watched: bool) -> None:
        self._submit("season", self._selected_season, watched)

    @Slot(bool)
    def setSeriesWatched(self, watched: bool) -> None:
        self._submit("series", None, watched)

    @Slot(str)
    def setStatus(self, status: str) -> None:
        if status in ("PLANNED", "WATCHING", "WATCHED"):
            self._submit("status", status, None)

    @Slot(bool)
    def setFavorite(self, favorite: bool) -> None:
        self._submit("favorite", favorite, None)

    @Slot()
    def removeFromLibrary(self) -> None:
        self._submit("status", None, None)

    @Slot(str)
    def addToList(self, name: str) -> None:
        self._submit("list", name, None)

    def _submit(self, action: str, value: Any, watched: bool | None) -> None:
        if not self._detail or self._saving or self._season_busy:
            return
        self._saving = True
        self._feedback = ""
        self.changed.emit()
        self._submit_future(
            self._save,
            self._generation,
            self._detail["id"],
            action,
            value,
            watched,
            self._selected_season,
        )

    def _save(
        self,
        generation: int,
        tv_id: int,
        action: str,
        value: Any,
        watched: bool | None,
        selected: int,
    ) -> None:
        try:
            if action == "episode":
                self._service.set_episode_watched(tv_id, selected, value, bool(watched))
            elif action == "season":
                self._service.set_bulk_watched(tv_id, selected, bool(watched))
            elif action == "series":
                self._service.set_bulk_watched(tv_id, None, bool(watched))
            elif action == "status":
                self._service.set_status(tv_id, value)
            elif action == "list":
                self._service.add_to_list(tv_id, value)
            else:
                self._service.set_favorite(tv_id, bool(value))
            detail = self._service.cached(tv_id) or {}
            episodes = self._service.cached_season(tv_id, selected) or []
        except (TMDbError, OSError, ValueError, LookupError, KeyError, SQLAlchemyError):
            self._saved.emit(generation, {}, [], "Değişiklik kaydedilemedi.")
        else:
            self._saved.emit(generation, detail, episodes, "Kaydedildi.")

    @Slot(int, object, object, str)
    def _apply_saved(
        self,
        generation: int,
        detail: dict[str, Any],
        episodes: list[dict[str, Any]],
        feedback: str,
    ) -> None:
        if generation != self._generation:
            return
        self._saving = False
        self._feedback = feedback
        if detail:
            self._detail = {
                **detail,
                "poster": self._detail.get("poster", ""),
                "backdrop": self._detail.get("backdrop", ""),
                "similar": self._detail.get("similar", []),
                "recommendations": self._detail.get("recommendations", []),
                "cast": self._detail.get("cast", []),
            }
            self._set_episodes(episodes)
        self.changed.emit()
        if detail:
            self.libraryChanged.emit()

    @Slot()
    def openTrailer(self) -> None:
        url = self._detail.get("trailerUrl", "")
        if url.startswith("https://www.youtube.com/watch?v="):
            QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def openProviderLink(self) -> None:
        """Open only TMDb's provider link returned for the TR region."""
        url = self._detail.get("providerLink", "")
        if url.startswith("https://www.themoviedb.org/"):
            QDesktopServices.openUrl(QUrl(url))

    def close(self) -> None:
        self._generation += 1
        self._season_generation += 1
        self._cancel_futures()
        self._executor.shutdown(wait=True, cancel_futures=True)
        if self._own_images and self._images is not None:
            self._images.close()
        for images in self._retired_images:
            images.close()
        self._retired_images.clear()
        self._service.close()
