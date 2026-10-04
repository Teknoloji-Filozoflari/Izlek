"""Offline movie library selection, sorting, favorites, and QML layout."""

from concurrent.futures import Future
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QColor, QGuiApplication, QImage
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.security.token_store import StoredToken
from izlek.services.continue_watching import ContinueWatchingService
from izlek.services.movie_library import MovieLibraryService
from izlek.ui.controllers.continue_watching_controller import ContinueWatchingController
from izlek.ui.controllers.movie_library_controller import MovieLibraryController
from izlek.ui.controllers.token_controller import TokenController


def _seed(factory):
    with factory.begin() as session:
        media = MediaRepository(session)
        users = UserMediaRepository(session)
        rows = (
            (1, "Zulu", date(2021, 1, 1), 6.0, TrackingStatus.PLANNED, False, 1),
            (2, "Bravo", date(2024, 1, 1), 8.5, TrackingStatus.PLANNED, True, 2),
            (3, "Alpha", None, None, TrackingStatus.PLANNED, False, 3),
            (4, "Watched", date(2022, 1, 1), 9.0, TrackingStatus.WATCHED, True, 4),
            (5, "Watching", date(2020, 1, 1), 5.0, TrackingStatus.WATCHING, False, 5),
            (6, "Favorite only", None, None, None, True, 6),
        )
        for tmdb_id, title, release, score, status, favorite, day in rows:
            item = media.upsert(
                tmdb_id,
                MediaType.MOVIE,
                title,
                release_date=release,
                poster_path=f"/{tmdb_id}.jpg",
                metadata_json={"detail": {"vote_average": score}},
            )
            if status:
                user = users.set_status(item.id, status)
            else:
                user = users.set_favorite(item.id, True)
            if favorite:
                users.set_favorite(item.id, True)
            user.added_at = datetime(2024, 1, day)
        # Cached search results without local membership do not enter the library.
        media.upsert(7, MediaType.MOVIE, "Search only")
        media.upsert(8, MediaType.TV, "A show")


def test_movie_library_filters_sorts_and_counts(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    _seed(factory)
    service = MovieLibraryService(factory)
    assert [item.tmdb_id for item in service.snapshot().items] == [3, 2, 1]
    assert [item.tmdb_id for item in service.snapshot(sort_by="title").items] == [
        3,
        2,
        1,
    ]
    assert [item.tmdb_id for item in service.snapshot(sort_by="year").items] == [
        2,
        1,
        3,
    ]
    assert [item.tmdb_id for item in service.snapshot(sort_by="score").items] == [
        2,
        1,
        3,
    ]
    watched = service.snapshot(TrackingStatus.WATCHED)
    assert [item.tmdb_id for item in watched.items] == [4]
    assert [item.tmdb_id for item in watched.favorites] == [6, 4, 2]
    assert watched.stats == {"total": 5, "planned": 3, "watching": 1, "watched": 1}
    assert service.snapshot(TrackingStatus.WATCHING).items[0].tmdb_id == 5
    assert {item.tmdb_id for item in service.snapshot(None).items} == {1, 2, 3, 4, 5}
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


def _wait_for(application, predicate):
    for _ in range(100):
        application.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Movie library did not load")


def test_movies_page_status_grid_and_compact_sections(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    application = QGuiApplication.instance() or QGuiApplication([])
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    _seed(factory)
    library = MovieLibraryController(
        service=MovieLibraryService(factory), images=_Images()
    )
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
        movie_library_controller=library,
        continue_controller=continuing,
    )
    try:
        window.navigate(1)
        _wait_for(application, lambda: not library.busy and len(library.items) == 5)
        grid = window.findChild(QQuickItem, "movieLibraryGrid")
        tabs = window.findChild(QQuickItem, "movieStatusTabs")
        sort_box = window.findChild(QQuickItem, "movieSort")
        favorite_strip = window.findChild(QQuickItem, "favoriteMoviesStrip")
        stats = window.findChild(QQuickItem, "movieStats")
        assert all(item is not None for item in (grid, tabs, sort_box, favorite_strip))
        assert stats is None
        assert not tabs.isVisible()
        assert not window.findChild(QQuickItem, "showsContinueSection").isVisible()
        assert favorite_strip.property("count") == 3
        for width, height in ((800, 600), (1366, 768), (1920, 1080)):
            window.resize(width, height)
            application.processEvents()
            assert grid.width() > 0 and grid.height() > 150
            assert grid.height() < 330
            assert favorite_strip.height() < 120
            assert grid.property("columns") >= (4 if width == 800 else 6)
        QTest.qWait(300)
        application.processEvents()
        sort_box.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Down)
        _wait_for(application, lambda: library.sortBy == "title" and not library.busy)
        assert [item["tmdb_id"] for item in library.items] == [3, 2, 4, 5, 1]
        QTest.qWait(300)
        grid.setProperty("currentIndex", 2)
        application.processEvents()

        def visible_favorite(item):
            if item.objectName() == "cardFavorite" and item.isVisible():
                return item
            return next(
                (
                    found
                    for child in item.childItems()
                    if (found := visible_favorite(child)) is not None
                ),
                None,
            )

        _wait_for(
            application,
            lambda: (
                visible_favorite(grid.property("currentItem")) is not None
                and visible_favorite(grid.property("currentItem")).property("checked")
                is True
            ),
        )
        card_favorite = visible_favorite(grid.property("currentItem"))
        card_favorite.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        _wait_for(application, lambda: not library.busy and len(library.favorites) == 2)
        with factory() as session:
            media = MediaRepository(session).get_by_tmdb(4, MediaType.MOVIE)
            user = UserMediaRepository(session).get(media.id)
            assert user.favorite is False
            assert user.status == TrackingStatus.WATCHED
        assert not warnings
    finally:
        window.close()
        library.close()
        continuing.close()
        application.processEvents()
        qInstallMessageHandler(previous)
        engine.dispose()


def test_movies_page_empty_state(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    application = QGuiApplication.instance() or QGuiApplication([])
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    library = MovieLibraryController(
        service=MovieLibraryService(create_session_factory(engine)), images=_Images()
    )
    continuing = ContinueWatchingController(
        service=ContinueWatchingService(create_session_factory(engine)),
        images=_Images(),
    )
    application, qml_engine, window = create_application(
        token_controller=TokenController(store=_Store()),
        movie_library_controller=library,
        continue_controller=continuing,
    )
    try:
        window.navigate(1)
        _wait_for(application, lambda: not library.busy and bool(library.stats))
        empty = window.findChild(QQuickItem, "movieLibraryEmpty")
        assert empty is not None and empty.isVisible()
        assert library.items == [] and library.favorites == []
        assert library.stats["total"] == 0
    finally:
        window.close()
        library.close()
        continuing.close()
        application.processEvents()
        engine.dispose()


def test_library_displays_real_posters_after_refresh_and_sort(tmp_path):
    application = QGuiApplication.instance() or QGuiApplication([])
    poster = QImage(34, 51, QImage.Format.Format_RGB32)
    poster.fill(QColor("red"))
    path = tmp_path / "poster.img"
    assert poster.save(str(path), "JPEG")
    requests = []

    class LocalImages:
        def poster(self, remote_path):
            requests.append(remote_path)
            future = Future()
            future.set_result(path)
            return future

    engine = initialize_database(tmp_path / "library.sqlite3")
    factory = create_session_factory(engine)
    _seed(factory)
    library = MovieLibraryController(
        service=MovieLibraryService(factory), images=LocalImages()
    )
    application, qml_engine, window = create_application(
        token_controller=TokenController(store=_Store()),
        movie_library_controller=library,
    )

    def cards(item):
        found = []
        if item.property("posterReady") is not None:
            found.append(item)
        for child in item.childItems():
            found.extend(cards(child))
        return found

    try:
        window.navigate(1)
        grid = window.findChild(QQuickItem, "movieLibraryGrid")
        initial_requests = None
        for action in (
            lambda: None, library.refresh, lambda: library.setSort("title"),
            lambda: (window.navigate(2), window.navigate(1)),
        ):
            action()
            application.processEvents()
            current_page = window.findChild(QQuickItem, "contentStack").property(
                "currentItem"
            )
            grid = current_page.findChild(QQuickItem, "movieLibraryGrid")
            _wait_for(application, lambda: not library.busy and len(library.items) == 5)
            QTest.qWait(150)
            _wait_for(
                application,
                lambda grid=grid: (
                    len(cards(grid)) >= 3
                    and all(card.property("posterReady") for card in cards(grid))
                ),
            )
            assert all(item["poster"].endswith("poster.img") for item in library.items)
            if initial_requests is None:
                initial_requests = len(requests)
            else:
                assert len(requests) == initial_requests
    finally:
        window.close()
        library.close()
        application.processEvents()
        engine.dispose()


def test_poster_arrival_preserves_card_focus_and_refresh_has_no_overlay(tmp_path):
    from shiboken6 import isValid

    application = QGuiApplication.instance() or QGuiApplication([])
    image = QImage(34, 51, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    path = tmp_path / "focus-poster.jpg"
    assert image.save(str(path), "JPEG")
    pending = {}

    class PendingImages:
        def poster(self, remote_path):
            return pending.setdefault(remote_path, Future())

    engine = initialize_database(tmp_path / "focus.sqlite3")
    factory = create_session_factory(engine)
    _seed(factory)
    library = MovieLibraryController(MovieLibraryService(factory), PendingImages())
    application, qml, window = create_application(
        token_controller=TokenController(store=_Store()),
        movie_library_controller=library,
    )
    try:
        window.navigate(1)
        _wait_for(application, lambda: not library.busy and bool(pending))
        grid = window.findChild(QQuickItem, "movieLibraryGrid")
        card = grid.property("currentItem")
        card.forceActiveFocus()
        data = card.property("modelData")
        if hasattr(data, "toVariant"):
            data = data.toVariant()
        remote_path = data["poster_path"]
        pending[remote_path].set_result(path)
        _wait_for(application, lambda: isValid(card) and card.property("posterReady"))
        assert grid.property("currentItem") is card
        assert card.hasActiveFocus()
        library.refresh()
        assert library.busy
        assert not window.findChild(QQuickItem, "libraryLoadingState").isVisible()
        assert window.findChild(QQuickItem, "libraryGridFrame").property("clip")
    finally:
        window.close()
        library.close()
        application.processEvents()
        engine.dispose()
