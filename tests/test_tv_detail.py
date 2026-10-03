"""TV detail, bulk progress, and restart behavior with mocked TMDb HTTP."""

from concurrent.futures import Future
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from PySide6.QtCore import QObject, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus, utc_now
from izlek.repositories.local import MediaRepository, SeasonRepository
from izlek.security.token_store import StoredToken
from izlek.services.tv_detail import TvDetailService
from izlek.services.tv_status import TvProgress, automatic_status
from izlek.tmdb.client import NetworkError, TmdbClient
from izlek.ui.controllers.token_controller import TokenController
from izlek.ui.controllers.tv_detail_controller import TvDetailController


def payloads():
    tv = {
        "id": 77,
        "name": "Çeviri",
        "original_name": "Original Show",
        "original_language": "en",
        "first_air_date": "2022-03-01",
        "last_air_date": "2024-04-01",
        "status": "Ended",
        "overview": "Story",
        "vote_average": 8.2,
        "genres": [{"id": 18, "name": "Dram"}],
        "created_by": [{"id": 1, "name": "Creator"}],
        "production_companies": [{"id": 2, "name": "Studio"}],
        "production_countries": [{"iso_3166_1": "US", "name": "ABD"}],
        "seasons": [
            {"id": 700, "season_number": 1, "name": "Season 1", "episode_count": 2},
            {"id": 701, "season_number": 2, "name": "Season 2", "episode_count": 1},
        ],
    }
    data = {
        "/3/tv/77": tv,
        "/3/tv/77/credits": {
            "id": 77,
            "cast": [{"id": 3, "name": "Actor", "character": "Lead", "order": 0}],
        },
        "/3/tv/77/videos": {
            "id": 77,
            "results": [
                {
                    "key": "abc_123",
                    "site": "YouTube",
                    "type": "Trailer",
                    "name": "Trailer",
                }
            ],
        },
        "/3/tv/77/similar": {
            "page": 1,
            "total_pages": 1,
            "total_results": 1,
            "results": [{"id": 88, "name": "Çeviri", "original_name": "Similar Show"}],
        },
        "/3/tv/77/recommendations": {
            "page": 1,
            "total_pages": 1,
            "total_results": 0,
            "results": [],
        },
        "/3/tv/77/watch/providers": {
            "id": 77,
            "results": {
                "TR": {
                    "link": "https://www.themoviedb.org/tv/77/watch?locale=TR",
                    "flatrate": [{"provider_id": 1, "provider_name": "Stream"}],
                }
            },
        },
    }
    for season_number, count in ((1, 2), (2, 1)):
        data[f"/3/tv/77/season/{season_number}"] = {
            "id": 699 + season_number,
            "season_number": season_number,
            "name": f"Season {season_number}",
            "episodes": [
                {
                    "id": 1000 + season_number * 10 + number,
                    "episode_number": number,
                    "name": f"Original Episode {season_number}-{number}",
                    "air_date": "2023-01-01",
                    "overview": "Episode story",
                    "still_path": "/still.jpg",
                }
                for number in range(1, count + 1)
            ],
        }
    return data


def test_tv_progress_bulk_refresh_and_restart(tmp_path):
    data = payloads()
    online = True
    requested = []

    def respond(request):
        requested.append((request.url.path, request.url.params.get("language")))
        if not online:
            raise httpx.ConnectError("offline")
        return httpx.Response(200, json=data[request.url.path])

    path = tmp_path / "izlek.sqlite3"
    engine = initialize_database(path)
    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        service = TvDetailService(
            TmdbClient(http_client, token="test-only"), create_session_factory(engine)
        )
        detail = service.load(77)
        assert len(requested) == 6
        assert detail["title"] == "Original Show"
        assert detail["seriesStatus"] == "Sona erdi"
        assert detail["creators"] == ["Creator"]
        assert detail["cast"][0]["name"] == "Actor"
        assert detail["companies"] == ["Studio"]
        assert detail["countries"] == ["ABD"]
        assert detail["providers"]["Abonelik"] == ["Stream"]
        assert detail["providerLink"] == "https://www.themoviedb.org/tv/77/watch?locale=TR"
        assert detail["trailerUrl"].endswith("abc_123")
        assert detail["similar"][0]["title"] == "Similar Show"
        assert service.set_status(77, "WATCHING")["status"] == "WATCHING"
        assert service.cached(77)["statusIsManual"] is True
        assert service.set_favorite(77, True)["favorite"] is True
        assert service.add_to_list(77, "Dizilerim")["lists"] == ["Dizilerim"]
        assert service.load_season(77, 1)[0]["name"] == "Original Episode 1-1"
        assert service.needs_refresh(77) is False
        assert service.season_needs_refresh(77, 1) is False
        assert ("/3/tv/77/season/1", "en") in requested
        assert service.set_episode_watched(77, 1, 1, True)[0]["watched"]
        assert not service.cached_season(77, 1)[1]["watched"]

        # Refresh metadata without replacing local progress.
        data["/3/tv/77"]["original_name"] = "Renamed Show"
        data["/3/tv/77/season/1"]["episodes"][0]["name"] = "Renamed Episode"
        with create_session_factory(engine).begin() as session:
            media = MediaRepository(session).get_by_tmdb(77, MediaType.TV)
            media.last_synced_at = utc_now() - timedelta(hours=25)
            season = next(
                item
                for item in SeasonRepository(session).list_for_media(media.id)
                if item.season_number == 1
            )
            season.last_synced_at = utc_now() - timedelta(hours=25)
        assert service.needs_refresh(77) is True
        assert service.season_needs_refresh(77, 1) is True
        assert service.load(77)["title"] == "Renamed Show"
        assert service.load_season(77, 1)[0]["watched"]
        assert service.cached_season(77, 1)[0]["name"] == "Renamed Episode"
        assert service.needs_refresh(77) is False
        assert service.season_needs_refresh(77, 1) is False

        assert all(item["watched"] for item in service.set_bulk_watched(77, 1, True))
        assert not any(
            item["watched"] for item in service.set_bulk_watched(77, 1, False)
        )
        service.set_bulk_watched(77, None, True)
        assert all(item["watched"] for item in service.cached_season(77, 1))
        assert all(item["watched"] for item in service.cached_season(77, 2))
        service.set_bulk_watched(77, None, False)
        assert not any(item["watched"] for item in service.cached_season(77, 1))
        assert not any(item["watched"] for item in service.cached_season(77, 2))
        service.set_episode_watched(77, 2, 1, True)
        service.close()
    engine.dispose()

    reopened_engine = initialize_database(path)
    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        reopened = TvDetailService(
            TmdbClient(http_client, token="test-only"),
            create_session_factory(reopened_engine),
        )
        online = False
        assert reopened.load(77)["title"] == "Renamed Show"
        assert reopened.cached(77)["status"] == "WATCHING"
        assert reopened.cached(77)["favorite"] is True
        assert reopened.cached(77)["lists"] == ["Dizilerim"]
        assert reopened.load_season(77, 2)[0]["watched"]
        reopened.set_bulk_watched(77, None, True)
        assert all(item["watched"] for item in reopened.cached_season(77, 1))
        reopened.close()
    reopened_engine.dispose()


@pytest.mark.parametrize(
    ("current", "manual", "progress", "explicit_unwatch", "expected"),
    [
        (None, False, TvProgress(0, 2, 2, 0), False, None),
        (None, False, TvProgress(1, 2, 1, 0), False, TrackingStatus.WATCHING),
        (None, False, TvProgress(2, 2, 0, 0), False, TrackingStatus.WATCHED),
        (None, False, TvProgress(1, 1, 0, 1), False, TrackingStatus.WATCHING),
        (
            TrackingStatus.PLANNED,
            True,
            TvProgress(2, 2, 0, 0),
            False,
            TrackingStatus.PLANNED,
        ),
        (
            TrackingStatus.WATCHED,
            False,
            TvProgress(2, 3, 1, 0),
            False,
            TrackingStatus.WATCHED,
        ),
        (
            TrackingStatus.WATCHED,
            False,
            TvProgress(2, 3, 1, 0),
            True,
            TrackingStatus.WATCHING,
        ),
        (TrackingStatus.WATCHING, False, TvProgress(0, 2, 2, 0), True, None),
    ],
)
def test_automatic_status_rules(current, manual, progress, explicit_unwatch, expected):
    assert (
        automatic_status(
            current,
            manual=manual,
            progress=progress,
            explicit_unwatch=explicit_unwatch,
        )
        == expected
    )


def test_auto_status_and_new_episode_notice_without_demotion(tmp_path):
    data = payloads()
    data["/3/tv/77/season/2"]["episodes"][0]["air_date"] = "2999-01-01"

    def respond(request):
        return httpx.Response(200, json=data[request.url.path])

    path = tmp_path / "izlek.sqlite3"
    engine = initialize_database(path)
    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        service = TvDetailService(
            TmdbClient(http_client, token="test-only"), create_session_factory(engine)
        )
        assert service.load(77)["status"] == ""
        service.load_season(77, 1)
        service.load_season(77, 2)
        assert service.cached(77)["status"] == ""
        service.set_episode_watched(77, 1, 1, True)
        assert service.cached(77)["status"] == "WATCHING"
        service.set_episode_watched(77, 1, 2, True)
        completed = service.cached(77)
        assert completed["status"] == "WATCHED"
        assert completed["statusIsManual"] is False
        assert completed["airedEpisodeCount"] == 2

        data["/3/tv/77"]["seasons"][0]["episode_count"] = 3
        data["/3/tv/77/season/1"]["episodes"].append(
            {
                "id": 1013,
                "episode_number": 3,
                "name": "New Episode",
                "air_date": "2023-01-02",
            }
        )
        after_summary = service.load(77)
        assert after_summary["status"] == "WATCHED"
        assert after_summary["missingEpisodeMetadataCount"] == 1
        service.load_season(77, 1)
        new_episode = service.cached(77)
        assert new_episode["status"] == "WATCHED"
        assert new_episode["newUnwatchedEpisodes"] is True
        assert new_episode["unwatchedAiredCount"] == 1
        service.set_episode_watched(77, 1, 3, True)
        assert service.cached(77)["status"] == "WATCHED"
        service.set_episode_watched(77, 1, 3, False)
        assert service.cached(77)["status"] == "WATCHING"
        service.set_bulk_watched(77, None, False)
        assert service.cached(77)["status"] == ""
        service.close()
    engine.dispose()


def test_manual_tv_status_survives_progress_changes(tmp_path):
    data = payloads()
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=data[request.url.path])
        )
    ) as http_client:
        service = TvDetailService(
            TmdbClient(http_client, token="test-only"), create_session_factory(engine)
        )
        service.load(77)
        service.set_status(77, "PLANNED")
        service.set_bulk_watched(77, None, True)
        assert service.cached(77)["status"] == "PLANNED"
        service.set_status(77, "WATCHED")
        service.set_bulk_watched(77, None, False)
        assert service.cached(77)["status"] == "WATCHED"
        assert service.cached(77)["statusIsManual"] is True
        service.close()
    engine.dispose()


def test_controller_shows_new_episode_without_changing_watched_status(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    application = QGuiApplication.instance() or QGuiApplication([])
    data = payloads()
    data["/3/tv/77/season/2"]["episodes"][0]["air_date"] = "2999-01-01"
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=data[request.url.path])
        )
    ) as http_client:
        service = TvDetailService(
            TmdbClient(http_client, token="test-only"), create_session_factory(engine)
        )
        service.load(77)
        service.load_season(77, 1)
        service.load_season(77, 2)
        service.set_bulk_watched(77, 1, True)
        assert service.cached(77)["status"] == "WATCHED"
        data["/3/tv/77"]["seasons"][0]["episode_count"] = 3
        data["/3/tv/77/season/1"]["episodes"].append(
            {
                "id": 1013,
                "episode_number": 3,
                "name": "New Episode",
                "air_date": "2023-01-02",
            }
        )
        with create_session_factory(engine).begin() as session:
            media = MediaRepository(session).get_by_tmdb(77, MediaType.TV)
            media.last_synced_at = utc_now() - timedelta(hours=25)
            season = next(
                item
                for item in SeasonRepository(session).list_for_media(media.id)
                if item.season_number == 1
            )
            season.last_synced_at = utc_now() - timedelta(hours=25)
        controller = TvDetailController(service=service, images=FakeImages())
        try:
            token = TokenController(store=ExistingTokenStore())
            application, qml_engine, window = create_application(
                token_controller=token, tv_controller=controller
            )
            window.openMediaDetail("tv", 77)
            wait_for(
                application,
                lambda: (
                    not controller.busy
                    and not controller.seasonBusy
                    and controller.detail.get("newUnwatchedEpisodes", False)
                ),
            )
            assert controller.detail["status"] == "WATCHED"
            assert controller.detail["unwatchedAiredCount"] == 1
            assert len(controller.episodes) == 3
            notice = window.findChild(QQuickItem, "newEpisodesNotice")
            assert notice is not None and notice.isVisible()
        finally:
            window.close()
            controller.close()
            application.processEvents()
    engine.dispose()


def test_bulk_refuses_incomplete_series_without_partial_changes(tmp_path):
    data = payloads()

    def respond(request):
        if request.url.path.endswith("/season/2"):
            raise httpx.ConnectError("offline")
        return httpx.Response(200, json=data[request.url.path])

    engine = initialize_database(tmp_path / "izlek.sqlite3")
    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        service = TvDetailService(
            TmdbClient(http_client, token="test-only"), create_session_factory(engine)
        )
        service.load(77)
        service.load_season(77, 1)
        with pytest.raises(NetworkError):
            service.set_bulk_watched(77, None, True)
        assert not any(item["watched"] for item in service.cached_season(77, 1))
        service.close()
    engine.dispose()


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

    def still(self, path):
        return self._done()


def wait_for(application, predicate):
    for _ in range(100):
        application.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Timed out waiting for TV state")


def test_tv_controller_episode_action_updates_state(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    application = QGuiApplication.instance() or QGuiApplication([])
    data = payloads()
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=data[request.url.path])
        )
    ) as http_client:
        service = TvDetailService(
            TmdbClient(http_client, token="test-only"), create_session_factory(engine)
        )
        controller = TvDetailController(service=service, images=FakeImages())
        try:
            controller.loadTv(77)
            wait_for(
                application, lambda: not controller.busy and not controller.seasonBusy
            )
            assert controller.detail["title"] == "Original Show"
            assert controller.selectedSeason == 1
            assert len(controller.episodes) == 2
            controller.setEpisodeWatched(1, True)
            wait_for(application, lambda: not controller.saving)
            assert controller.episodes[0]["watched"]
            controller.setSeasonWatched(False)
            wait_for(application, lambda: not controller.saving)
            assert not controller.episodes[0]["watched"]
        finally:
            controller.close()
    engine.dispose()


class ExistingTokenStore:
    def load(self):
        return StoredToken("test-only", "keyring")


def test_tv_page_bulk_requires_confirmation(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    application = QGuiApplication.instance() or QGuiApplication([])
    data = payloads()
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    warnings = []

    def collect(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    handler = qInstallMessageHandler(collect)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=data[request.url.path])
        )
    ) as http_client:
        service = TvDetailService(
            TmdbClient(http_client, token="test-only"), create_session_factory(engine)
        )
        tv = TvDetailController(service=service, images=FakeImages())
        token = TokenController(store=ExistingTokenStore())
        application, qml_engine, window = create_application(
            token_controller=token, tv_controller=tv
        )
        try:
            window.openMediaDetail("tv", 77)
            wait_for(application, lambda: not tv.busy and not tv.seasonBusy)
            stack = window.findChild(QQuickItem, "contentStack")
            assert stack.property("currentItem").property("pageTitle") == "Dizi Detayı"
            providers = window.findChild(QQuickItem, "tvProviders")
            assert providers is not None and providers.isVisible()
            provider_link = providers.findChild(QQuickItem, "providerLinkButton")
            assert provider_link is not None and provider_link.isVisible()
            for width, height in ((1366, 768), (1920, 1080)):
                window.resize(width, height)
                application.processEvents()
                assert window.width() == width
                assert window.height() == height
            list_open = window.findChild(QQuickItem, "tvListOpen")
            list_open.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Space)
            list_dialog = window.findChild(QObject, "tvListDialog")
            wait_for(application, lambda: list_dialog.property("opened"))
            list_name = window.findChild(QQuickItem, "tvListName")
            list_name.setProperty("text", "Dizi Listesi")
            list_add = window.findChild(QQuickItem, "tvListAdd")
            list_add.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Space)
            wait_for(application, lambda: tv.detail.get("lists") == ["Dizi Listesi"])
            button = window.findChild(QQuickItem, "seasonWatched")
            button.forceActiveFocus()
            QTest.keyClick(window, " ")
            dialog = window.findChild(QObject, "tvBulkDialog")
            wait_for(application, lambda: dialog.property("opened"))
            assert not any(item["watched"] for item in tv.episodes)
            dialog.accept()
            wait_for(application, lambda: all(item["watched"] for item in tv.episodes))
            assert not warnings
        finally:
            window.close()
            tv.close()
            application.processEvents()
            qInstallMessageHandler(handler)
    engine.dispose()
