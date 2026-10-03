"""Offline TV library progress and shared QML presentation."""

from concurrent.futures import Future
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import (
    EpisodeRepository,
    MediaRepository,
    SeasonRepository,
    UserMediaRepository,
)
from izlek.security.token_store import StoredToken
from izlek.services.continue_watching import ContinueWatchingService
from izlek.services.tv_library import TvLibraryService
from izlek.ui.controllers.continue_watching_controller import ContinueWatchingController
from izlek.ui.controllers.token_controller import TokenController
from izlek.ui.controllers.tv_library_controller import TvLibraryController


def _seed(factory):
    with factory.begin() as session:
        media = MediaRepository(session)
        users = UserMediaRepository(session)
        seasons = SeasonRepository(session)
        episodes = EpisodeRepository(session)
        current = media.upsert(
            101,
            MediaType.TV,
            "Current Show",
            first_air_date=date(2022, 1, 1),
            poster_path="/current.jpg",
            metadata_json={
                "detail": {
                    "vote_average": 8.2,
                    "seasons": [
                        {"season_number": 0, "episode_count": 2},
                        {"season_number": 1, "episode_count": 3},
                        {"season_number": 2, "episode_count": 2},
                    ],
                }
            },
        )
        user = users.set_status(current.id, TrackingStatus.WATCHING)
        user.added_at = datetime(2024, 1, 1)
        users.set_favorite(current.id, True)
        special = seasons.upsert(current.id, 0)
        special_ep = episodes.upsert(special.id, 1, air_date=date(2020, 1, 1))
        episodes.set_watched(special_ep.id, True)
        season1 = seasons.upsert(current.id, 1)
        for number in (1, 2):
            episode = episodes.upsert(
                season1.id, number, air_date=date(2022, 1, number)
            )
            episodes.set_watched(episode.id, True)
        episodes.upsert(season1.id, 3, air_date=date(2999, 1, 1))
        season2 = seasons.upsert(current.id, 2)
        episodes.upsert(season2.id, 1, air_date=date(2023, 1, 1))
        episodes.upsert(season2.id, 1, air_date=date(2023, 1, 1))
        episodes.upsert(season2.id, 2, air_date=None)

        completed = media.upsert(
            102,
            MediaType.TV,
            "Completed Show",
            metadata_json={
                "detail": {"seasons": [{"season_number": 1, "episode_count": 24}]}
            },
        )
        users.set_status(completed.id, TrackingStatus.WATCHED)
        users.set_favorite(completed.id, True)
        season = seasons.upsert(completed.id, 1)
        for number in range(1, 13):
            episode = episodes.upsert(season.id, number, air_date=date(2020, 1, 1))
            episodes.set_watched(episode.id, True)

        planned = media.upsert(
            103,
            MediaType.TV,
            "Planned Show",
            metadata_json={
                "detail": {"seasons": [{"season_number": 1, "episode_count": 8}]}
            },
        )
        users.set_status(planned.id, TrackingStatus.PLANNED)

        favorite_only = media.upsert(104, MediaType.TV, "Favorite only")
        users.set_favorite(favorite_only.id, True)
        media.upsert(105, MediaType.TV, "Search result only")
        movie = media.upsert(106, MediaType.MOVIE, "Movie")
        users.set_status(movie.id, TrackingStatus.WATCHING)


def test_tv_library_progress_favorites_and_status_counts(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    _seed(factory)
    service = TvLibraryService(factory)
    current = service.snapshot(TrackingStatus.WATCHING, today=date(2026, 10, 3))
    assert len(current.items) == 1
    assert current.items[0].tmdb_id == 101
    assert current.items[0].progress_text == "S02E01"
    assert current.items[0].progress == 2 / 5
    assert current.items[0].year == "2022"
    assert current.stats == {"total": 3, "planned": 1, "watching": 1, "watched": 1}
    assert {item.tmdb_id for item in current.favorites} == {101, 102, 104}
    unknown = next(item for item in current.favorites if item.tmdb_id == 104)
    assert unknown.progress_text == "" and unknown.progress == -1
    watched = service.snapshot(TrackingStatus.WATCHED)
    assert watched.items[0].progress_text == "12 / 24 bölüm"
    assert watched.items[0].progress == 0.5
    planned = service.snapshot(TrackingStatus.PLANNED)
    assert planned.items[0].progress_text == "0 / 8 bölüm"
    assert service.snapshot(TrackingStatus.WATCHING, "score").items[0].score == 8.2
    engine.dispose()


class _Store:
    def load(self):
        return StoredToken("test-only", "keyring")


class _Images:
    def poster(self, path):
        future = Future()
        future.set_result(
            Path(__file__).resolve().parents[1]
            / "src/izlek/resources/images/poster-placeholder.svg"
        )
        return future

    def backdrop(self, path):
        return self.poster(path)


def _wait_for(application, predicate):
    for _ in range(100):
        application.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("TV library did not load")


def test_shows_page_tabs_progress_and_compact_sections(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    application = QGuiApplication.instance() or QGuiApplication([])
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    _seed(factory)
    library = TvLibraryController(service=TvLibraryService(factory), images=_Images())
    continuing = ContinueWatchingController(
        service=ContinueWatchingService(factory), images=_Images()
    )
    warnings = []

    def collect(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous = qInstallMessageHandler(collect)
    application, qml_engine, window = create_application(
        token_controller=TokenController(store=_Store()),
        tv_library_controller=library,
        continue_controller=continuing,
    )
    try:
        window.navigate(2)
        _wait_for(application, lambda: not library.busy and bool(library.stats))
        assert [item["tmdb_id"] for item in library.items] == [103]
        grid = window.findChild(QQuickItem, "tvLibraryGrid")
        tabs = window.findChild(QQuickItem, "tvStatusTabs")
        favorites = window.findChild(QQuickItem, "favoriteShowsStrip")
        stats = window.findChild(QQuickItem, "tvStats")
        assert all(item is not None for item in (grid, tabs, favorites, stats))
        assert favorites.property("count") == 3
        for width, height in ((800, 600), (1366, 768), (1920, 1080)):
            window.resize(width, height)
            application.processEvents()
            assert grid.height() < 330 and favorites.height() < 120
            assert stats.mapToScene(QPointF(0, stats.height())).y() <= height
        second_tab = tabs.childItems()[0].childItems()[1]
        second_tab.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        _wait_for(
            application, lambda: library.status == "WATCHING" and not library.busy
        )
        assert library.items[0]["progress_text"] == "S02E01"
        QTest.qWait(300)
        application.processEvents()
        card = grid.property("currentItem")
        assert card is not None and card.property("progressText") == "S02E01"
        assert not warnings
    finally:
        window.close()
        library.close()
        continuing.close()
        application.processEvents()
        qInstallMessageHandler(previous)
        engine.dispose()
