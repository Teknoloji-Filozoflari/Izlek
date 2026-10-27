"""Smart lists, user tags, theme preference and cache size label."""

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.security.token_store import StoredToken
from izlek.services.custom_lists import CustomListsService
from izlek.services.smart_lists import SMART_ID_UNWATCHED_FAVORITES, tag_list_id
from izlek.services.tags import TagsService
from izlek.ui.controllers.cache_controller import format_bytes
from izlek.ui.controllers.theme_controller import ThemeController
from izlek.ui.controllers.token_controller import TokenController


class _Store:
    def load(self):
        return StoredToken("test-only", "keyring")


def test_format_bytes_uses_compact_turkish_units():
    assert format_bytes(0) == "0 B"
    assert format_bytes(512) == "512 B"
    assert format_bytes(1536) == "1.5 KB"
    assert format_bytes(5 * 1024 * 1024) == "5.0 MB"


def test_smart_lists_match_favorites_status_and_ratings(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session)
        users = UserMediaRepository(session)
        movie = media.upsert(1, MediaType.MOVIE, "Favori Film")
        show = media.upsert(2, MediaType.TV, "İzlenen Dizi")
        planned = media.upsert(3, MediaType.MOVIE, "Plan")
        rated = media.upsert(4, MediaType.MOVIE, "Yüksek")
        users.set_favorite(movie.id, True)
        users.set_status(movie.id, TrackingStatus.PLANNED)
        users.set_status(show.id, TrackingStatus.WATCHING)
        users.set_status(planned.id, TrackingStatus.PLANNED)
        users.set_personal(rated.id, 9, "Harika")
    service = CustomListsService(factory)
    try:
        snap = service.snapshot(SMART_ID_UNWATCHED_FAVORITES)
        unwatched = next(
            item for item in snap["lists"] if item["key"] == "unwatched_favorites"
        )
        assert unwatched["count"] == 1
        assert [item["title"] for item in snap["items"]] == ["Favori Film"]
        watching = service.snapshot(
            next(item["id"] for item in snap["lists"] if item["key"] == "watching")
        )
        assert [item["title"] for item in watching["items"]] == ["İzlenen Dizi"]
        rated_snap = service.snapshot(
            next(item["id"] for item in snap["lists"] if item["key"] == "highly_rated")
        )
        assert [item["title"] for item in rated_snap["items"]] == ["Yüksek"]
        with pytest.raises(ValueError, match="Akıllı"):
            service.add(SMART_ID_UNWATCHED_FAVORITES, "movie", 1)
    finally:
        service.close()
        engine.dispose()


def test_tags_attach_and_appear_as_smart_lists(tmp_path):
    engine = initialize_database(tmp_path / "tags.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(9, MediaType.MOVIE, "Etiketli")
        UserMediaRepository(session).set_status(media.id, TrackingStatus.PLANNED)
    tags = TagsService(factory)
    lists = CustomListsService(factory)
    try:
        assert tags.create("Noir") > 0
        assert tags.set_for_media("movie", 9, ["Noir", "Gece"]) == ["Gece", "Noir"]
        assert tags.names_for("movie", 9) == ["Gece", "Noir"]
        snap = lists.snapshot()
        tag_entries = [item for item in snap["lists"] if item["key"].startswith("tag:")]
        assert {item["name"] for item in tag_entries} == {
            "Etiket: Gece",
            "Etiket: Noir",
        }
        noir = next(item for item in tag_entries if item["name"].endswith("Noir"))
        members = lists.snapshot(noir["id"])["items"]
        assert [item["title"] for item in members] == ["Etiketli"]
        assert members[0]["tags"] == ["Gece", "Noir"]
        assert tag_list_id(int(noir["key"].split(":")[1])) == noir["id"]
        tags.remove_from_media("movie", 9, "Noir")
        assert tags.names_for("movie", 9) == ["Gece"]
    finally:
        tags.close()
        lists.close()
        engine.dispose()


def test_theme_controller_persists_light_mode(tmp_path):
    path = tmp_path / "window.ini"
    settings = QSettings(str(path), QSettings.Format.IniFormat)
    controller = ThemeController(settings=settings)
    assert controller.mode == "dark"
    controller.setMode("light")
    assert controller.isLight
    settings.sync()
    reopened = ThemeController(
        settings=QSettings(str(path), QSettings.Format.IniFormat)
    )
    assert reopened.mode == "light"
    reopened.setMode("bogus")
    assert reopened.mode == "light"


def test_settings_shows_cache_size_and_theme_control(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    application, engine, window = create_application(
        token_controller=TokenController(store=_Store())
    )
    try:
        window.navigate(5)
        QTest.qWait(400)
        size = window.findChild(QQuickItem, "cacheSizeLabel")
        theme = window.findChild(QQuickItem, "themeModeControl")
        assert size is not None
        assert "Mevcut cache boyutu" in size.property("text")
        assert theme is not None
        assert theme.property("currentIndex") in (0, 1)
        theme_controller = engine.rootContext().contextProperty("themeController")
        theme_controller.setMode("light")
        QTest.qWait(100)
        assert theme.property("currentIndex") == 1
    finally:
        window.close()
        application.processEvents()
