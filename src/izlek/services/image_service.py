"""Background TMDb image retrieval with offline disk-cache fallback."""

import re
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import RLock
from time import sleep
from typing import Literal

import httpx

from izlek.cache.images import ImageDiskCache
from izlek.tmdb.client import TmdbClient, TMDbError

PosterSize = Literal["grid", "detail"]
_POSTER_TARGETS = {"grid": 342, "detail": 780}
_BACKDROP_TARGET = 1280
_IMAGE_TIMEOUT = 8.0
_MAX_IMAGE_BYTES = 15 * 1024 * 1024
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9._/-]+$")
_SAFE_SIZE = re.compile(r"^w[0-9]+$")
_PLACEHOLDER_DIR = Path(__file__).resolve().parents[1] / "resources/images"


def _select_size(sizes: list[str], target: int) -> str:
    """Choose the smallest available width at or above the target."""
    candidates = sorted(
        (int(size[1:]), size)
        for size in sizes
        if _SAFE_SIZE.fullmatch(size)
    )
    if not candidates:
        raise ValueError("No usable TMDb image size")
    return next(
        (size for width, size in candidates if width >= target),
        candidates[-1][1],
    )


def _valid_image(content: bytes, content_type: str) -> bool:
    media_type = content_type.split(";", 1)[0].strip().lower()
    return (
        (media_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff")
         and content.endswith(b"\xff\xd9"))
        or (media_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n")
            and content[-8:-4] == b"IEND")
        or (media_type == "image/webp" and content.startswith(b"RIFF")
            and content[8:12] == b"WEBP"
            and int.from_bytes(content[4:8], "little") + 8 == len(content))
    )


class ImageService:
    """Return local image paths from worker futures; never download on the UI thread."""

    def __init__(
        self,
        tmdb: TmdbClient,
        *,
        cache: ImageDiskCache | None = None,
        http_client: httpx.Client | None = None,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        self._tmdb = tmdb
        self.cache = cache or ImageDiskCache()
        self._http = http_client or httpx.Client(follow_redirects=False)
        self._own_http = http_client is None
        self._executor = executor or ThreadPoolExecutor(max_workers=4)
        self._own_executor = executor is None
        self._lock = RLock()
        self._configuration_lock = RLock()
        self._pending: dict[tuple[str, str], Future[Path]] = {}
        self._configuration = None

    def poster(self, path: str | None, size: PosterSize = "grid") -> Future[Path]:
        """Resolve a grid or detail poster without blocking the caller."""
        if size not in _POSTER_TARGETS:
            raise ValueError("Unknown poster size")
        return self._submit("poster-" + size, path)

    def backdrop(self, path: str | None) -> Future[Path]:
        """Resolve a backdrop without blocking the caller."""
        return self._submit("backdrop", path)

    def profile(self, path: str | None) -> Future[Path]:
        """Resolve an actor portrait through the same offline image cache."""
        return self._submit("profile", path)

    def still(self, path: str | None) -> Future[Path]:
        """Resolve an episode still at a practical card size."""
        return self._submit("still", path)

    def cache_size_async(self) -> Future[int]:
        """Measure disposable cache storage off the UI thread."""
        return self._executor.submit(self.cache.size_bytes)

    def close(self) -> None:
        """Release resources owned by this service."""
        if self._own_executor:
            self._executor.shutdown(wait=True, cancel_futures=True)
        if self._own_http:
            self._http.close()

    def _submit(self, kind: str, path: str | None) -> Future[Path]:
        placeholder = self._placeholder(kind)
        if not path or not _SAFE_PATH.fullmatch(path) or ".." in path.split("/"):
            completed: Future[Path] = Future()
            completed.set_result(placeholder)
            return completed
        key = (kind, path)
        with self._lock:
            if key in self._pending:
                return self._pending[key]
            future = self._executor.submit(self._download, kind, path)
            self._pending[key] = future
            future.add_done_callback(lambda done: self._forget(key, done))
            return future

    def _forget(self, key: tuple[str, str], future: Future[Path]) -> None:
        with self._lock:
            if self._pending.get(key) is future:
                del self._pending[key]

    def _cached_image(self, kind: str, path: str) -> Path | None:
        cached = self.cache.get(kind, path)
        if cached is None and kind == "poster-grid":
            # A detail poster already has enough resolution for a list/card.
            cached = self.cache.get("poster-detail", path)
        return cached

    def _placeholder(self, kind: str) -> Path:
        name = (
            "backdrop-placeholder.svg"
            if kind in ("backdrop", "still")
            else "poster-placeholder.svg"
        )
        return _PLACEHOLDER_DIR / name

    def _download(self, kind: str, path: str) -> Path:
        """Retry a transient network/CDN failure once before showing fallback."""
        for attempt in range(2):
            try:
                return self._download_once(kind, path)
            except (TMDbError, httpx.RequestError):
                if attempt == 1:
                    return self._placeholder(kind)
                sleep(0.25)
            except (OSError, ValueError):
                return self._placeholder(kind)
        return self._placeholder(kind)

    def _download_once(self, kind: str, path: str) -> Path:
        placeholder = self._placeholder(kind)
        try:
            cached = self._cached_image(kind, path)
            if cached is not None:
                return cached
            with self._configuration_lock:
                if self._configuration is None:
                    self._configuration = self._tmdb.configuration().images
                images = self._configuration
            if kind == "backdrop":
                size = _select_size(images.backdrop_sizes, _BACKDROP_TARGET)
            elif kind == "still":
                size = _select_size(images.still_sizes or images.backdrop_sizes, 300)
            elif kind == "profile":
                size = _select_size(images.profile_sizes or images.poster_sizes, 185)
            else:
                size = _select_size(images.poster_sizes, _POSTER_TARGETS[kind[7:]])
            url = images.secure_base_url.rstrip("/") + "/" + size + path
            with self._http.stream("GET", url, timeout=_IMAGE_TIMEOUT) as response:
                if response.status_code in (408, 429) or response.status_code >= 500:
                    raise httpx.ConnectError("Temporary image download failure")
                if response.status_code != 200:
                    return placeholder
                if int(response.headers.get("Content-Length", "0")) > _MAX_IMAGE_BYTES:
                    return placeholder
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > _MAX_IMAGE_BYTES:
                        return placeholder
                data = bytes(content)
                if not _valid_image(data, response.headers.get("Content-Type", "")):
                    return placeholder
            return self.cache.put(kind, path, data)
        except (OSError, ValueError):
            return placeholder
