"""Image service behavior with local HTTP mocks and isolated XDG cache."""

import os
from datetime import UTC, datetime, timedelta
from threading import Event

import httpx

from izlek.cache.images import ImageDiskCache
from izlek.core.paths import app_paths
from izlek.services.image_service import ImageService
from izlek.tmdb.models import Configuration

JPEG = b"\xff\xd8\xff" + b"test-image" + b"\xff\xd9"


class FakeTmdb:
    def __init__(self):
        self.calls = 0

    def configuration(self):
        self.calls += 1
        return Configuration.model_validate(
            {
                "images": {
                    "secure_base_url": "https://images.example/",
                    "poster_sizes": ["w185", "w342", "w500", "w780", "original"],
                    "backdrop_sizes": ["w780", "w1280", "original"],
                    "still_sizes": ["w92", "w185", "w300", "original"],
                }
            }
        )


def make_service(tmp_path, tmdb, respond):
    http_client = httpx.Client(transport=httpx.MockTransport(respond))
    service = ImageService(
        tmdb, cache=ImageDiskCache(tmp_path / "cache/izlek/images"),
        http_client=http_client,
    )
    return service, http_client


def test_default_image_cache_uses_xdg_cache_not_data(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg-cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    cache = ImageDiskCache()
    assert cache.root == app_paths().cache / "images"
    assert app_paths().data not in cache.root.parents
    assert cache.size_bytes() == 0


def test_image_cache_discards_entries_older_than_six_month_retention(tmp_path):
    cache = ImageDiskCache(tmp_path / "cache")
    path = cache.put("poster-grid", "/old.jpg", b"image")
    expired = datetime.now(UTC) - timedelta(days=181)
    os.utime(path, (expired.timestamp(), expired.timestamp()))

    assert cache.get("poster-grid", "/old.jpg") is None
    assert not path.exists()


def test_image_cache_clear_removes_only_disposable_entries(tmp_path):
    cache = ImageDiskCache(tmp_path / "cache")
    cache.put("poster-grid", "/first.jpg", b"first")
    cache.put("backdrop", "/second.jpg", b"second")
    unrelated = cache.root / "keep.txt"
    unrelated.write_text("not an image cache entry", encoding="utf-8")

    assert cache.clear() == 2
    assert cache.size_bytes() == 0
    assert unrelated.read_text(encoding="utf-8") == "not an image cache entry"


def test_sizes_cache_hits_and_offline_fallback(tmp_path):
    urls = []
    tmdb = FakeTmdb()

    def respond(request):
        urls.append(str(request.url))
        return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG)

    service, http_client = make_service(tmp_path, tmdb, respond)
    try:
        grid = service.poster("/poster.jpg", "grid").result(timeout=2)
        detail = service.poster("/poster.jpg", "detail").result(timeout=2)
        backdrop = service.backdrop("/backdrop.jpg").result(timeout=2)
        still = service.still("/still.jpg").result(timeout=2)
        assert grid.read_bytes() == JPEG
        assert detail != grid
        assert backdrop.read_bytes() == JPEG
        assert still.read_bytes() == JPEG
        assert urls == [
            "https://images.example/w342/poster.jpg",
            "https://images.example/w780/poster.jpg",
            "https://images.example/w1280/backdrop.jpg",
            "https://images.example/w300/still.jpg",
        ]
        assert tmdb.calls == 1
        assert service.poster("/poster.jpg", "grid").result(timeout=2) == grid
        assert len(urls) == 4
        assert service.cache_size_async().result(timeout=2) == 4 * len(JPEG)
    finally:
        service.close()
        http_client.close()

    offline = FakeTmdb()
    service, http_client = make_service(
        tmp_path,
        offline,
        lambda request: (_ for _ in ()).throw(httpx.ConnectError("offline")),
    )
    try:
        assert service.poster("/poster.jpg", "grid").result(timeout=2) == grid
        assert offline.calls == 0
    finally:
        service.close()
        http_client.close()


def test_invalid_download_does_not_replace_cache(tmp_path):
    tmdb = FakeTmdb()
    response = [
        httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG)
    ]

    def respond(request):
        return response[0]

    service, http_client = make_service(tmp_path, tmdb, respond)
    try:
        cached = service.poster("/poster.jpg").result(timeout=2)
        response[0] = httpx.Response(
            200, headers={"Content-Type": "image/jpeg"}, content=b"broken"
        )
        assert service.poster("/poster.jpg").result(timeout=2) == cached
        assert cached.read_bytes() == JPEG
        assert service.poster("/broken.jpg").result(timeout=2).name == (
            "poster-placeholder.svg"
        )
        assert service.cache.get("poster-grid", "/broken.jpg") is None
    finally:
        service.close()
        http_client.close()


def test_missing_and_unsafe_paths_use_placeholders_without_network(tmp_path):
    tmdb = FakeTmdb()
    service, http_client = make_service(
        tmp_path, tmdb, lambda request: (_ for _ in ()).throw(AssertionError("network"))
    )
    try:
        poster_placeholder = service.poster(None).result()
        backdrop_placeholder = service.backdrop("").result()
        still_placeholder = service.still(None).result()
        assert poster_placeholder.name == "poster-placeholder.svg"
        assert backdrop_placeholder.name == "backdrop-placeholder.svg"
        assert still_placeholder.name == "backdrop-placeholder.svg"
        assert poster_placeholder.is_file()
        assert backdrop_placeholder.is_file()
        assert service.poster("/../secret").result().name == "poster-placeholder.svg"
        assert tmdb.calls == 0
        assert service.cache_size_async().result(timeout=2) == 0
        assert not service.cache.root.exists()
    finally:
        service.close()
        http_client.close()


def test_download_runs_in_worker_and_deduplicates_pending_requests(tmp_path):
    entered = Event()
    release = Event()
    calls = []

    def respond(request):
        calls.append(request)
        entered.set()
        assert release.wait(timeout=2)
        return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG)

    service, http_client = make_service(tmp_path, FakeTmdb(), respond)
    try:
        first = service.poster("/poster.jpg")
        assert entered.wait(timeout=2)
        second = service.poster("/poster.jpg")
        assert first is second
        assert not first.done()
        release.set()
        assert first.result(timeout=2).read_bytes() == JPEG
        assert len(calls) == 1
    finally:
        release.set()
        service.close()
        http_client.close()
