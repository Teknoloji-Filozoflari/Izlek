"""Image service behavior with local HTTP mocks and isolated XDG cache."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event, get_ident

import httpx
import pytest

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
                    "profile_sizes": ["w45", "w185", "h632", "original"],
                }
            }
        )


def make_service(tmp_path, tmdb, respond):
    http_client = httpx.Client(transport=httpx.MockTransport(respond))
    service = ImageService(
        tmdb,
        cache=ImageDiskCache(tmp_path / "cache/izlek/images"),
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


def test_actor_profile_uses_profile_sizes_and_reuses_disk_cache(tmp_path):
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG)

    service, client = make_service(tmp_path, FakeTmdb(), respond)
    try:
        path = service.profile("/actor.jpg").result(timeout=2)
        assert path.read_bytes() == JPEG
        assert calls == ["https://images.example/w185/actor.jpg"]
    finally:
        service.close()
        client.close()

    offline = FakeTmdb()
    service, client = make_service(
        tmp_path, offline,
        lambda request: (_ for _ in ()).throw(AssertionError("Repeated download")),
    )
    try:
        assert service.profile("/actor.jpg").result(timeout=2) == path
        assert offline.calls == 0
    finally:
        service.close()
        client.close()


def test_cached_image_lookup_runs_off_the_callers_thread(tmp_path):
    entered, release = Event(), Event()
    caller = get_ident()

    class SlowCache(ImageDiskCache):
        def get(self, kind, image_path):
            assert get_ident() != caller
            entered.set()
            assert release.wait(timeout=2)
            return super().get(kind, image_path)

    cache = SlowCache(tmp_path / "slow-cache")
    path = cache.put("poster-grid", "/cached.jpg", JPEG)
    service = ImageService(FakeTmdb(), cache=cache)
    try:
        future = service.poster("/cached.jpg")
        assert entered.wait(timeout=1)
        assert not future.done()
        release.set()
        assert future.result(timeout=2) == path
    finally:
        release.set()
        service.close()


def test_slow_configuration_does_not_block_other_image_requests(tmp_path):
    entered, release = Event(), Event()

    class SlowTmdb(FakeTmdb):
        def configuration(self):
            entered.set()
            assert release.wait(timeout=2)
            return super().configuration()

    service, client = make_service(
        tmp_path, SlowTmdb(),
        lambda request: httpx.Response(
            200, headers={"Content-Type": "image/jpeg"}, content=JPEG
        ),
    )
    callers = ThreadPoolExecutor(max_workers=1)
    try:
        first = service.poster("/first.jpg")
        assert entered.wait(timeout=1)
        # Scheduling the next card must return while the first CDN setup waits.
        second = callers.submit(service.poster, "/second.jpg").result(timeout=0.5)
        release.set()
        assert first.result(timeout=2).read_bytes() == JPEG
        assert second.result(timeout=2).read_bytes() == JPEG
    finally:
        release.set()
        callers.shutdown(wait=True)
        service.close()
        client.close()


def test_image_cache_discards_entries_older_than_six_month_retention(tmp_path):
    cache = ImageDiskCache(tmp_path / "cache")
    path = cache.put("poster-grid", "/old.jpg", b"image")
    expired = datetime.now(UTC) - timedelta(days=181)
    os.utime(path, (expired.timestamp(), expired.timestamp()))

    assert cache.get("poster-grid", "/old.jpg") is None
    assert not path.exists()


def test_expired_images_are_removed_without_being_requested_again(tmp_path):
    cache = ImageDiskCache(tmp_path / "cache")
    old = cache.put("poster-grid", "/old.jpg", JPEG)
    fresh = cache.put("poster-grid", "/fresh.jpg", JPEG)
    expired = datetime.now(UTC) - timedelta(days=181)
    os.utime(old, (expired.timestamp(), expired.timestamp()))
    assert cache.prune_expired() == 1
    assert not old.exists()
    assert fresh.read_bytes() == JPEG


def test_cache_measurement_handles_concurrent_removal(tmp_path, monkeypatch):
    from pathlib import Path

    cache = ImageDiskCache(tmp_path / "cache")
    path = cache.put("poster-grid", "/poster.jpg", JPEG)
    original_is_file = Path.is_file

    def racing_is_file(candidate):
        exists = original_is_file(candidate)
        if candidate == path and exists:
            candidate.unlink()
        return exists

    monkeypatch.setattr(Path, "is_file", racing_is_file)
    assert cache.size_bytes() == 0


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


def test_grid_reuses_detail_poster_after_restart_without_any_network(tmp_path):
    service, client = make_service(
        tmp_path, FakeTmdb(),
        lambda request: httpx.Response(
            200, headers={"Content-Type": "image/jpeg"}, content=JPEG
        ),
    )
    try:
        detail = service.poster("/selected.jpg", "detail").result(timeout=2)
    finally:
        service.close()
        client.close()
    tmdb = FakeTmdb()
    service, client = make_service(
        tmp_path, tmdb,
        lambda request: (_ for _ in ()).throw(AssertionError("Repeated download")),
    )
    try:
        assert service.poster("/selected.jpg").result(timeout=2) == detail
        assert tmdb.calls == 0
    finally:
        service.close()
        client.close()


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


@pytest.mark.parametrize("failure", ["connection", 408, 429, 503])
def test_transient_image_failure_retries_and_caches_poster(tmp_path, failure):
    calls = []

    def respond(request):
        calls.append(request)
        if len(calls) == 1:
            if failure == "connection":
                raise httpx.ConnectError("offline")
            return httpx.Response(failure)
        return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG)

    service, client = make_service(tmp_path, FakeTmdb(), respond)
    try:
        path = service.poster("/poster.jpg").result(timeout=2)
        assert path.read_bytes() == JPEG
        assert len(calls) == 2
        assert service.poster("/poster.jpg").result() == path
        assert len(calls) == 2
    finally:
        service.close()
        client.close()


def test_image_retry_is_bounded_and_later_request_can_recover(tmp_path):
    calls = []
    available = False

    def respond(request):
        calls.append(request)
        if not available:
            raise httpx.ConnectError("offline")
        return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG)

    service, client = make_service(tmp_path, FakeTmdb(), respond)
    try:
        assert (
            service.poster("/poster.jpg").result(timeout=2).name
            == "poster-placeholder.svg"
        )
        assert len(calls) == 2
        available = True
        assert service.poster("/poster.jpg").result(timeout=2).read_bytes() == JPEG
        assert len(calls) == 3
    finally:
        service.close()
        client.close()
