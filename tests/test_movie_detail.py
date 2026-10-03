"""Movie detail metadata and local state with mocked TMDb HTTP."""

from concurrent.futures import Future
from datetime import timedelta
from pathlib import Path
from threading import Event

import httpx
import pytest
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtTest import QTest

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus, utc_now
from izlek.repositories.local import MediaRepository
from izlek.services.movie_detail import MovieDetailService
from izlek.tmdb.client import TmdbClient
from izlek.ui.controllers.movie_detail_controller import MovieDetailController


def responses():
    movie = {
        "id": 42,
        "title": "Türkçe Başlık",
        "original_title": "Original Film",
        "original_language": "en",
        "release_date": "2024-02-03",
        "runtime": 124,
        "vote_average": 7.6,
        "overview": "A film.",
        "poster_path": "/poster.jpg",
        "backdrop_path": "/backdrop.jpg",
        "genres": [{"id": 18, "name": "Dram"}],
        "production_companies": [{"id": 7, "name": "Studio"}],
        "production_countries": [{"iso_3166_1": "US", "name": "ABD"}],
    }
    return {
        "/3/movie/42": movie,
        "/3/movie/42/credits": {
            "id": 42,
            "cast": [{"id": 1, "name": "Actor", "character": "Lead", "order": 0}],
            "crew": [{"id": 2, "name": "Director", "job": "Director"}],
        },
        "/3/movie/42/videos": {
            "id": 42,
            "results": [
                {
                    "key": "abc_DEF-12",
                    "site": "YouTube",
                    "type": "Trailer",
                    "name": "Official Trailer",
                    "official": True,
                }
            ],
        },
        "/3/movie/42/similar": {
            "page": 1,
            "total_pages": 1,
            "total_results": 1,
            "results": [
                {"id": 10, "title": "Çeviri", "original_title": "Similar Original"}
            ],
        },
        "/3/movie/42/recommendations": {
            "page": 1,
            "total_pages": 1,
            "total_results": 1,
            "results": [
                {"id": 11, "title": "Çeviri", "original_title": "Recommended Original"}
            ],
        },
        "/3/movie/42/watch/providers": {
            "id": 42,
            "results": {
                "TR": {
                    "link": "https://www.themoviedb.org/movie/42/watch?locale=TR",
                    "flatrate": [{"provider_id": 8, "provider_name": "Stream A"}],
                }
            },
        },
    }


class FakeImages:
    def _done(self):
        future = Future()
        future.set_result(
            Path(__file__).resolve().parents[1]
            / "src/izlek/resources/images/poster-placeholder.svg"
        )
        return future

    def poster(self, path, size="grid"):
        return self._done()

    def backdrop(self, path):
        return self._done()


def wait_for(application, predicate):
    for _ in range(100):
        application.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Timed out waiting for movie state")


def test_movie_sections_save_metadata_and_personal_state_survives_restart(tmp_path):
    payloads = responses()
    paths = []
    online = True

    def respond(request):
        paths.append(request.url.path)
        if not online:
            raise httpx.ConnectError("offline")
        return httpx.Response(200, json=payloads[request.url.path])

    database_file = tmp_path / "izlek.sqlite3"
    engine = initialize_database(database_file)
    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        service = MovieDetailService(
            TmdbClient(http_client, token="test-only"),
            create_session_factory(engine),
        )
        detail = service.load(42)
        assert set(paths) == set(payloads)
        assert len(paths) == 6
        assert detail["title"] == "Original Film"
        assert detail["runtime"] == 124
        assert detail["genres"] == ["Dram"]
        assert detail["score"] == 7.6
        assert detail["cast"] == [{"name": "Actor", "character": "Lead"}]
        assert detail["directors"] == ["Director"]
        assert detail["companies"] == ["Studio"]
        assert detail["countries"] == ["ABD"]
        assert detail["providers"]["Abonelik"] == ["Stream A"]
        assert detail["trailerUrl"] == "https://www.youtube.com/watch?v=abc_DEF-12"
        assert detail["similar"][0]["title"] == "Similar Original"
        assert detail["recommendations"][0]["title"] == "Recommended Original"
        assert detail["status"] == ""
        assert detail["favorite"] is False

        assert service.set_favorite(42, True)["status"] == ""
        assert service.set_status(42, "PLANNED")["status"] == "PLANNED"
        assert service.set_status(42, "WATCHING")["status"] == "WATCHING"
        assert service.set_status(42, "WATCHED")["status"] == "WATCHED"
        assert service.cached(42)["favorite"] is True
        assert service.add_to_list(42, "Hafta Sonu")["lists"] == ["Hafta Sonu"]
        assert service.add_to_list(42, "hafta sonu")["lists"] == ["Hafta Sonu"]

        payloads["/3/movie/42"]["original_title"] = "Renamed Original"
        refreshed = service.load(42)
        assert refreshed["title"] == "Renamed Original"
        assert refreshed["status"] == "WATCHED"
        assert refreshed["favorite"] is True
        assert refreshed["lists"] == ["Hafta Sonu"]
        with create_session_factory(engine)() as session:
            media = MediaRepository(session).get_by_tmdb(42, MediaType.MOVIE)
            assert media.last_synced_at is not None
            assert media.metadata_json["detail"]["original_title"] == "Renamed Original"
        service.close()
    engine.dispose()

    reopened_engine = initialize_database(database_file)
    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        reopened = MovieDetailService(
            TmdbClient(http_client, token="test-only"),
            create_session_factory(reopened_engine),
        )
        online = False
        cached = reopened.load(42)
        assert cached["title"] == "Renamed Original"
        assert cached["status"] == "WATCHED"
        assert cached["favorite"] is True
        assert cached["lists"] == ["Hafta Sonu"]
        reopened.close()
    reopened_engine.dispose()


def test_movie_controller_actions_update_qml_state(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    application = QGuiApplication.instance() or QGuiApplication([])
    payloads = responses()
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payloads[request.url.path])
        )
    ) as http_client:
        service = MovieDetailService(
            TmdbClient(http_client, token="test-only"),
            create_session_factory(engine),
        )
        controller = MovieDetailController(service=service, images=FakeImages())
        try:
            controller.loadMovie(42)
            wait_for(application, lambda: not controller.busy)
            assert controller.detail["title"] == "Original Film"
            assert controller.detail["providerLink"] == (
                "https://www.themoviedb.org/movie/42/watch?locale=TR"
            )
            controller.setStatus("PLANNED")
            wait_for(application, lambda: not controller.saving)
            assert controller.detail["status"] == "PLANNED"
            controller.setFavorite(True)
            wait_for(application, lambda: not controller.saving)
            assert controller.detail["favorite"] is True
            controller.addToList("My List")
            wait_for(application, lambda: not controller.saving)
            assert controller.detail["lists"] == ["My List"]
            opened = []
            monkeypatch.setattr(
                QDesktopServices, "openUrl", lambda url: opened.append(url.toString())
            )
            controller.openTrailer()
            assert opened == ["https://www.youtube.com/watch?v=abc_DEF-12"]
            controller.openProviderLink()
            assert opened[-1] == "https://www.themoviedb.org/movie/42/watch?locale=TR"
        finally:
            controller.close()
    engine.dispose()


def test_optional_movie_section_failure_keeps_main_detail(tmp_path):
    payloads = responses()

    def respond(request):
        if request.url.path.endswith("/credits"):
            return httpx.Response(503)
        return httpx.Response(200, json=payloads[request.url.path])

    engine = initialize_database(tmp_path / "izlek.sqlite3")
    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        service = MovieDetailService(
            TmdbClient(http_client, token="test-only"),
            create_session_factory(engine),
        )
        try:
            detail = service.load(42)
            assert detail["title"] == "Original Film"
            assert detail["cast"] == []
            assert detail["trailerUrl"]
        finally:
            service.close()
    engine.dispose()


def test_movie_controller_uses_fresh_cache_then_refreshes_stale_in_background(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    application = QGuiApplication.instance() or QGuiApplication([])
    payloads = responses()
    paths = []
    block_refresh = False
    release_refresh = Event()

    def respond(request):
        paths.append(request.url.path)
        if block_refresh:
            assert release_refresh.wait(timeout=2)
        return httpx.Response(200, json=payloads[request.url.path])

    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        service = MovieDetailService(
            TmdbClient(http_client, token="test-only"), factory
        )
        service.load(42)
        service.set_status(42, "WATCHED")
        service.set_favorite(42, True)
        controller = MovieDetailController(service=service, images=FakeImages())
        try:
            paths.clear()
            controller.loadMovie(42)
            wait_for(
                application,
                lambda: not controller.busy and controller.detail.get("title")
                == "Original Film",
            )
            QTest.qWait(50)
            assert paths == []

            with factory.begin() as session:
                media = MediaRepository(session).get_by_tmdb(42, MediaType.MOVIE)
                media.last_synced_at = utc_now() - timedelta(hours=25)
            payloads["/3/movie/42"]["original_title"] = "Background Refresh"
            block_refresh = True
            controller.loadMovie(42)
            wait_for(
                application,
                lambda: not controller.busy and controller.detail.get("title")
                == "Original Film",
            )
            assert controller.detail["status"] == TrackingStatus.WATCHED
            assert controller.detail["favorite"] is True
            release_refresh.set()
            wait_for(
                application,
                lambda: controller.detail.get("title") == "Background Refresh",
            )
            assert paths
            assert controller.detail["status"] == TrackingStatus.WATCHED
            assert controller.detail["favorite"] is True
        finally:
            release_refresh.set()
            controller.close()
    engine.dispose()


def test_movie_controller_ignores_result_after_page_cancel(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    application = QGuiApplication.instance() or QGuiApplication([])
    started = Event()
    release = Event()

    class SlowService:
        client = object()

        def cached(self, movie_id):
            return None

        def load(self, movie_id):
            started.set()
            assert release.wait(timeout=2)
            return {"id": movie_id, "title": "Geç gelen sonuç"}

        def close(self):
            pass

    controller = MovieDetailController(service=SlowService(), images=FakeImages())
    try:
        controller.loadMovie(42)
        assert started.wait(timeout=1)
        controller.cancelPending()
        release.set()
        QTest.qWait(50)
        application.processEvents()
        assert controller.detail == {}
        assert controller.busy is False
    finally:
        release.set()
        controller.close()


@pytest.mark.parametrize("failure", ["offline", "timeout", "not-found"])
def test_stale_movie_cache_survives_refresh_failure(tmp_path, monkeypatch, failure):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    application = QGuiApplication.instance() or QGuiApplication([])
    payloads = responses()
    failing = False

    def respond(request):
        if failing:
            if failure == "offline":
                raise httpx.ConnectError("offline")
            if failure == "timeout":
                raise httpx.ReadTimeout("timeout")
            return httpx.Response(404)
        return httpx.Response(200, json=payloads[request.url.path])

    engine = initialize_database(tmp_path / f"{failure}.sqlite3")
    factory = create_session_factory(engine)
    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        service = MovieDetailService(
            TmdbClient(http_client, token="test-only"), factory
        )
        service.load(42)
        with factory.begin() as session:
            media = MediaRepository(session).get_by_tmdb(42, MediaType.MOVIE)
            media.last_synced_at = utc_now() - timedelta(hours=25)
        failing = True
        controller = MovieDetailController(service=service, images=FakeImages())
        try:
            controller.loadMovie(42)
            wait_for(
                application,
                lambda: not controller.busy and bool(controller.detail),
            )
            QTest.qWait(100)
            application.processEvents()
            assert controller.detail["title"] == "Original Film"
            assert controller.error == ""
        finally:
            controller.close()
    engine.dispose()
