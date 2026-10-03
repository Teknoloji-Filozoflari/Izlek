"""Mixed local favorites remain independent of tracking status."""

from datetime import date

import pytest

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.services.favorites import FavoritesService


def test_favorites_include_movie_and_tv_without_tracking_status(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session)
        users = UserMediaRepository(session)
        movie = media.upsert(
            42, MediaType.MOVIE, "Original Film", release_date=date(2020, 1, 1)
        )
        show = media.upsert(
            42, MediaType.TV, "Original Show", first_air_date=date(2024, 1, 1)
        )
        users.set_favorite(movie.id, True)
        users.set_status(show.id, TrackingStatus.WATCHING)
        users.set_favorite(show.id, True)
        movie_id, show_id = movie.id, show.id

    service = FavoritesService(factory)
    assert {(item.kind, item.tmdb_id, item.year) for item in service.list_all()} == {
        ("movie", 42, "2020"),
        ("tv", 42, "2024"),
    }
    service.set_favorite("tv", 42, False)
    with factory.begin() as session:
        media = MediaRepository(session)
        media.upsert(42, MediaType.MOVIE, "Original Film", poster_path="/new.jpg")
        assert UserMediaRepository(session).get(movie_id).status is None
        assert (
            UserMediaRepository(session).get(show_id).status == TrackingStatus.WATCHING
        )
    assert [(item.kind, item.title) for item in service.list_all()] == [
        ("movie", "Original Film")
    ]
    service.set_favorite("movie", 42, False)
    assert service.list_all() == []
    engine.dispose()


def test_favorite_update_rejects_unknown_media_without_creating_rows(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    service = FavoritesService(factory)
    try:
        with pytest.raises(LookupError, match="Medya bulunamadı"):
            service.set_favorite("movie", 404, True)
        assert service.list_all() == []
    finally:
        service.close()
        engine.dispose()


def test_home_favorites_limit_and_expand(tmp_path, monkeypatch):
    from PySide6.QtCore import Qt, QtMsgType, qInstallMessageHandler
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuick import QQuickItem
    from PySide6.QtTest import QTest

    from izlek.app import create_application
    from izlek.security.token_store import StoredToken
    from izlek.ui.controllers.favorites_controller import FavoritesController
    from izlek.ui.controllers.token_controller import TokenController

    class Store:
        def load(self):
            return StoredToken("test-only", "keyring")

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    application = QGuiApplication.instance() or QGuiApplication([])
    engine = initialize_database(tmp_path / "favorites.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session)
        users = UserMediaRepository(session)
        for tmdb_id in range(1, 8):
            item = media.upsert(tmdb_id, MediaType.MOVIE, f"Film {tmdb_id}")
            users.set_favorite(item.id, True)
    favorites = FavoritesController(FavoritesService(factory))
    warnings = []

    def collect(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous = qInstallMessageHandler(collect)
    application, qml_engine, window = create_application(
        token_controller=TokenController(store=Store()),
        favorites_controller=favorites,
    )
    try:
        for _ in range(100):
            application.processEvents()
            if len(favorites.items) == 7:
                break
            QTest.qWait(10)
        assert len(favorites.items) == 7
        button = window.findChild(QQuickItem, "allFavoritesButton")
        assert button is not None and button.isVisible()
        assert button.property("text") == "Tümünü Gör"
        button.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        application.processEvents()
        assert button.property("text") == "Daha Az Göster"
        assert not warnings
    finally:
        window.close()
        favorites.close()
        application.processEvents()
        qInstallMessageHandler(previous)
        engine.dispose()
