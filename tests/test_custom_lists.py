"""Local custom-list membership, ordering and QML navigation."""

import pytest
from PySide6.QtCore import QPointF, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlExpression
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.security.token_store import StoredToken
from izlek.services.custom_lists import CustomListsService
from izlek.ui.controllers.custom_lists_controller import CustomListsController
from izlek.ui.controllers.token_controller import TokenController


def test_custom_lists_crud_membership_and_order_survive_restart(tmp_path):
    path = tmp_path / "izlek.sqlite3"
    engine = initialize_database(path)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session)
        users = UserMediaRepository(session)
        movie = media.upsert(42, MediaType.MOVIE, "Film")
        media.upsert(42, MediaType.TV, "Dizi")
        users.set_status(movie.id, TrackingStatus.PLANNED)
        movie_id = movie.id
    service = CustomListsService(factory)
    first = service.create("Hafta Sonu")
    second = service.create("Arşiv")
    with pytest.raises(ValueError):
        service.create("  hafta sonu  ")
    service.add(first, "movie", 42)
    service.add(first, "tv", 42)
    service.add(first, "movie", 42)
    service.add(second, "movie", 42)
    assert service.snapshot(first)["lists"] == [
        {"id": first, "name": "Hafta Sonu", "count": 2},
        {"id": second, "name": "Arşiv", "count": 1},
    ]
    assert [
        (item["kind"], item["title"]) for item in service.snapshot(first)["items"]
    ] == [("movie", "Film"), ("tv", "Dizi")]
    service.move_item(first, "tv", 42, -1)
    service.move_list(second, -1)
    service.rename(first, "İzlenecekler")
    service.close()
    engine.dispose()

    reopened_engine = initialize_database(path)
    reopened = CustomListsService(create_session_factory(reopened_engine))
    assert [item["name"] for item in reopened.snapshot(first)["lists"]] == [
        "Arşiv",
        "İzlenecekler",
    ]
    assert [item["kind"] for item in reopened.snapshot(first)["items"]] == [
        "tv",
        "movie",
    ]
    assert reopened.add_by_name("tv", 42, "İZLENECEKLER") == first
    assert len(reopened.snapshot(first)["items"]) == 2
    reopened.remove(first, "movie", 42)
    assert [item["kind"] for item in reopened.snapshot(first)["items"]] == ["tv"]
    assert [item["kind"] for item in reopened.snapshot(second)["items"]] == ["movie"]
    reopened.delete(first)
    assert [item["name"] for item in reopened.snapshot()["lists"]] == ["Arşiv"]
    with create_session_factory(reopened_engine)() as session:
        assert (
            UserMediaRepository(session).get(movie_id).status == TrackingStatus.PLANNED
        )
    reopened.close()
    reopened_engine.dispose()


def test_custom_list_validation_and_missing_records_are_safe(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    service = CustomListsService(create_session_factory(engine))
    try:
        for name in ("", "   ", "x" * 201):
            with pytest.raises(ValueError, match="1–200"):
                service.create(name)
        with pytest.raises(LookupError, match="Liste bulunamadı"):
            service.rename(404, "Yeni ad")
        with pytest.raises(LookupError, match="Medya"):
            service.add_by_name("movie", 404, "Yeni liste")
        assert service.snapshot() == {
            "lists": [],
            "items": [],
            "candidates": [],
            "selected_id": 0,
        }
    finally:
        service.close()
        engine.dispose()


class _Store:
    def load(self):
        return StoredToken("test-only", "keyring")


def _wait_for(application, predicate):
    for _ in range(100):
        application.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Liste sayfası güncellenmedi")


def test_lists_page_create_rename_add_remove_and_empty_state(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    application = QGuiApplication.instance() or QGuiApplication([])
    engine = initialize_database(tmp_path / "lists.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        MediaRepository(session).upsert(17, MediaType.MOVIE, "Local Film")
        MediaRepository(session).upsert(17, MediaType.TV, "Local Dizi")
    controller = CustomListsController(CustomListsService(factory))
    warnings = []

    def collect(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous = qInstallMessageHandler(collect)
    application, qml_engine, window = create_application(
        token_controller=TokenController(store=_Store()),
        custom_lists_controller=controller,
    )
    try:
        window.navigate(3)
        _wait_for(application, lambda: not controller.busy)
        for width, height in ((1366, 768), (1920, 1080)):
            window.resize(width, height)
            application.processEvents()
            assert window.width() == width and window.height() == height
        assert controller.lists == []
        create = window.findChild(QQuickItem, "createListButton")
        create.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        dialog = window.findChild(QQuickItem, "listNameInput")
        dialog.setProperty("text", "Deneme")
        QTest.keyClick(window, Qt.Key.Key_Return)
        _wait_for(
            application, lambda: len(controller.lists) == 1 and not controller.busy
        )
        assert controller.lists[0]["name"] == "Deneme"
        assert controller.items == []
        picker = window.findChild(QQuickItem, "listMediaPicker")
        picker.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        QTest.qWait(100)
        view = QQmlExpression(
            qml_engine.rootContext(), picker, "popup.contentItem"
        ).evaluate()[0]

        def labels(item, name="filterOptionLabel"):
            result = [item] if item.objectName() == name else []
            for child in item.childItems():
                result.extend(labels(child, name))
            return result

        options = labels(view)
        assert len(options) == 2
        assert {option.property("text") for option in options} == {
            "Local Film · Film", "Local Dizi · Dizi"
        }
        for option in options:
            point = option.mapToScene(QPointF(option.width() / 2, option.height() / 2))
            QTest.mouseMove(window, point.toPoint())
            QTest.qWait(50)
            assert all(label.isVisible() for label in options)
            assert all(label.parentItem().isVisible() for label in options)
        QTest.keyClick(window, Qt.Key.Key_Escape)
        assert window.property("currentIndex") == 3
        search_input = window.findChild(QQuickItem, "listMediaSearchInput")
        search_button = window.findChild(QQuickItem, "searchListMediaButton")
        search_input.setProperty("text", "  LOCAL film  ")
        search_button.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        application.processEvents()
        assert [item["kind"] for item in controller.candidates] == ["movie"]
        search_input.setProperty("text", "olmayan başlık")
        search_input.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Return)
        application.processEvents()
        assert controller.candidates == []
        add_button = window.findChild(QQuickItem, "addMediaToListButton")
        assert not add_button.isEnabled()
        search_input.setProperty("text", "film")
        QTest.keyClick(window, Qt.Key.Key_Return)
        application.processEvents()
        add_button.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        _wait_for(
            application, lambda: len(controller.items) == 1 and not controller.busy
        )
        _wait_for(application, lambda: bool(controller.items[0]["poster"]))
        assert controller.items[0]["kind"] == "movie"
        assert controller.candidates == []
        clear_button = window.findChild(QQuickItem, "clearListMediaSearchButton")
        clear_button.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        application.processEvents()
        assert search_input.property("text") == ""
        assert [item["kind"] for item in controller.candidates] == ["tv"]
        media_view = window.findChild(QQuickItem, "customListMedia")
        _wait_for(application, lambda: bool(labels(media_view, "customListPoster")))
        poster = labels(media_view, "customListPoster")[0]
        ready = QQmlExpression(qml_engine.rootContext(), poster, "status === 1")
        _wait_for(application, lambda: ready.evaluate()[0])
        controller.renameList(controller.selectedId, "Yeni Ad")
        _wait_for(application, lambda: controller.lists[0]["name"] == "Yeni Ad")
        controller.removeMedia(controller.selectedId, "movie", 17)
        _wait_for(application, lambda: not controller.items and not controller.busy)
        assert not warnings
    finally:
        window.close()
        controller.close()
        application.processEvents()
        qInstallMessageHandler(previous)
        engine.dispose()


def test_list_posters_for_movie_and_tv_persist_and_ignore_stale_updates(tmp_path):
    import httpx

    from test_image_service import JPEG, FakeTmdb, make_service

    application = QGuiApplication.instance() or QGuiApplication([])
    engine = initialize_database(tmp_path / "posters.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        repo = MediaRepository(session)
        repo.upsert(42, MediaType.MOVIE, "Film", poster_path="/movie.jpg")
        repo.upsert(42, MediaType.TV, "Dizi", poster_path="/tv.jpg")
    service = CustomListsService(factory)
    selected = service.create("Afişler")
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG)

    images, client = make_service(tmp_path, FakeTmdb(), respond)
    controller = CustomListsController(service, images=images)
    try:
        controller.selectList(selected)
        _wait_for(application, lambda: not controller.busy)
        for kind in ("movie", "tv"):
            controller.addMedia(selected, kind, 42)
            _wait_for(application, lambda: not controller.busy)
        _wait_for(application, lambda: all(item["poster"] for item in controller.items))
        posters = {item["kind"]: item["poster"] for item in controller.items}
        assert posters["movie"] != posters["tv"]
        assert len(calls) == 2
        controller._apply_poster(controller._generation - 1, "tv", 42, "stale")
        assert controller.items[1]["poster"] == posters["tv"]
    finally:
        controller.close()
        images.close()
        client.close()
    offline = FakeTmdb()
    images, client = make_service(
        tmp_path, offline,
        lambda request: (_ for _ in ()).throw(AssertionError("Repeated download")),
    )
    controller = CustomListsController(CustomListsService(factory), images=images)
    try:
        controller.selectList(selected)
        _wait_for(application, lambda: len(controller.items) == 2
                  and all(item["poster"] for item in controller.items))
        assert {item["kind"]: item["poster"] for item in controller.items} == posters
        assert offline.calls == 0
    finally:
        controller.close()
        images.close()
        client.close()
        engine.dispose()
