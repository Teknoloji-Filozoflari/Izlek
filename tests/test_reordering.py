"""Atomic multi-add and persisted mouse ordering across media types."""

import json
from threading import Event, Thread

import pytest
from PySide6.QtCore import QObject, QPoint, QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.services.custom_lists import CustomListsService
from izlek.services.library_order import LibraryOrderService
from izlek.services.movie_library import MovieLibraryService
from izlek.services.transfer import TransferService
from izlek.services.tv_library import TvLibraryService
from izlek.ui.controllers.custom_lists_controller import CustomListsController
from izlek.ui.controllers.movie_library_controller import MovieLibraryController
from izlek.ui.controllers.token_controller import TokenController
from izlek.ui.controllers.tv_library_controller import TvLibraryController
from test_global_search import ExistingTokenStore, FakeImages, wait_for


@pytest.fixture
def ordered_factory(tmp_path):
    path = tmp_path / "order.sqlite3"
    engine = initialize_database(path)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        for kind in MediaType:
            for item_id in (1, 2, 3):
                media = MediaRepository(session).upsert(
                    item_id, kind, f"Item {item_id}"
                )
                user = UserMediaRepository(session).set_status(
                    media.id, TrackingStatus.WATCHING
                )
                user.favorite = item_id == 1
    try:
        yield factory
    finally:
        engine.dispose()


def test_batch_add_validates_all_members_and_deduplicates(ordered_factory):
    service = CustomListsService(ordered_factory)
    list_id = service.create("Multi")
    with pytest.raises(LookupError):
        service.add_many(
            list_id, [{"kind": "movie", "tmdb_id": 1}, {"kind": "tv", "tmdb_id": 999}]
        )
    assert service.snapshot(list_id)["items"] == []
    service.add_many(
        list_id,
        [
            {"kind": "movie", "tmdb_id": 1},
            {"kind": "tv", "tmdb_id": 1},
            {"kind": "movie", "tmdb_id": 1},
            {"kind": "movie", "tmdb_id": 2},
        ],
    )
    assert [
        (row["kind"], row["tmdb_id"]) for row in service.snapshot(list_id)["items"]
    ] == [("movie", 1), ("tv", 1), ("movie", 2)]
    service.reorder_item(list_id, "movie", 1, "movie", 2)
    restarted = CustomListsService(ordered_factory)
    assert [
        (row["kind"], row["tmdb_id"]) for row in restarted.snapshot(list_id)["items"]
    ] == [("tv", 1), ("movie", 2), ("movie", 1)]


@pytest.mark.parametrize("kind", list(MediaType))
def test_library_order_preserves_tracking_and_survives_export(
    ordered_factory,
    tmp_path,
    kind,
):
    ordering = LibraryOrderService(ordered_factory)
    before = TransferService(ordered_factory).build_export()
    ordering.move(kind, 1, 3, [1, 2, 3])
    service = MovieLibraryService if kind == MediaType.MOVIE else TvLibraryService
    assert [
        row.tmdb_id for row in service(ordered_factory).snapshot(None, "custom").items
    ] == [2, 3, 1]
    # Sorting by title does not destroy the user's saved manual order.
    assert [
        row.tmdb_id for row in service(ordered_factory).snapshot(None, "title").items
    ] == [1, 2, 3]
    after = TransferService(ordered_factory).build_export()
    assert [(row.media_type, row.tmdb_id, row.status) for row in before.tracking] == [
        (row.media_type, row.tmdb_id, row.status) for row in after.tracking
    ]
    assert before.favorites == after.favorites
    path = tmp_path / "backup.json"
    TransferService(ordered_factory).export_file(path)
    target = initialize_database(tmp_path / "imported.sqlite3")
    try:
        factory = create_session_factory(target)
        TransferService(factory).import_file(path)
        assert [
            row.tmdb_id for row in service(factory).snapshot(None, "custom").items
        ] == [2, 3, 1]
    finally:
        target.dispose()


def test_old_backup_migrates_and_keeps_existing_manual_order(ordered_factory, tmp_path):
    transfer = TransferService(ordered_factory)
    payload = transfer.build_export().model_dump(mode="json")
    payload["schema_version"] = 1
    for row in payload["tracking"]:
        row.pop("sort_order")
    path = tmp_path / "old.json"
    path.write_text(json.dumps(payload))
    LibraryOrderService(ordered_factory).move(MediaType.MOVIE, 1, 3, [1, 2, 3])
    assert transfer.read_file(path).schema_version == 4
    transfer.import_file(path)
    assert [
        row.tmdb_id
        for row in MovieLibraryService(ordered_factory).snapshot(None, "custom").items
    ] == [2, 3, 1]


def _visual(item, name):
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = _visual(child, name)
        if found is not None:
            return found
    return None


def _drag(window, source, destination):
    start = source.mapToScene(QPointF(source.width() / 2, source.height() / 2))
    # Cross startDragDistance before the path so MouseArea enters dragging under
    # offscreen/software Qt (Nix CI) as reliably as on desktop PySide wheels.
    threshold = float(QGuiApplication.styleHints().startDragDistance()) + 1.0
    primed = start + QPointF(threshold, threshold)
    QTest.mousePress(
        window,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        start.toPoint(),
    )
    QTest.mouseMove(window, primed.toPoint())
    for index in range(1, 9):
        point = primed + (destination - primed) * (index / 8)
        QTest.mouseMove(window, point.toPoint(), 15)
    QTest.mouseRelease(
        window,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        destination.toPoint(),
    )


@pytest.mark.parametrize("kind", ["movie", "tv"])
@pytest.mark.parametrize("surface", ["poster", "title"])
def test_mouse_drags_library_cards_without_opening_detail(
    ordered_factory, kind, surface
):
    controller_type = MovieLibraryController if kind == "movie" else TvLibraryController
    service_type = MovieLibraryService if kind == "movie" else TvLibraryService
    controller = controller_type(service_type(ordered_factory), images=FakeImages())
    kwargs = {
        "movie_library_controller"
        if kind == "movie"
        else "tv_library_controller": controller
    }
    app, engine, window = create_application(
        token_controller=TokenController(store=ExistingTokenStore()), **kwargs
    )
    try:
        window.resize(1366, 768)
        window.navigate(1 if kind == "movie" else 2)
        wait_for(app, lambda: len(controller.items) == 3 and not controller.busy)
        grid = window.findChild(
            QQuickItem, "movieLibraryGrid" if kind == "movie" else "tvLibraryGrid"
        )
        before = [row["tmdb_id"] for row in controller.items]
        card = grid.property("currentItem")
        assert _visual(card, "cardReorderHandle") is None
        handle = _visual(card, "cardDragArea")
        assert handle is not None and handle.isVisible()
        assert not handle.property("showHandle")
        destination = grid.mapToScene(
            QPointF(grid.property("cellWidth") * 2.5, grid.property("cellHeight") / 2)
        )
        _drag(
            window,
            handle if surface == "poster" else _visual(card, "cardTitle"),
            destination,
        )
        expected = before[1:] + before[:1]
        wait_for(app, lambda: [row["tmdb_id"] for row in controller.items] == expected)
        assert controller.sortBy == "custom"
        assert window.findChild(QQuickItem, "contentStack").property("depth") == 1
        controller.refresh()
        wait_for(app, lambda: not controller.busy)
        assert [row["tmdb_id"] for row in controller.items] == expected
    finally:
        window.close()
        for child in engine.children():
            if callable(getattr(child, "close", None)):
                child.close()
        app.processEvents()


def test_mouse_drags_custom_list_members(ordered_factory):
    service = CustomListsService(ordered_factory)
    list_id = service.create("Drag")
    service.add_many(list_id, [{"kind": "movie", "tmdb_id": i} for i in (1, 2, 3)])
    controller = CustomListsController(service, images=FakeImages())
    app, engine, window = create_application(
        token_controller=TokenController(store=ExistingTokenStore()),
        custom_lists_controller=controller,
    )
    try:
        window.resize(1366, 768)
        window.navigate(3)
        controller.selectList(list_id)
        wait_for(app, lambda: len(controller.items) == 3 and not controller.busy)
        view = window.findChild(QQuickItem, "customListMedia")
        wait_for(
            app,
            lambda: view is not None
            and view.isVisible()
            and len(_all_visual(view, "listMediaReorderHandle")) == 3,
        )
        handles = sorted(
            _all_visual(view, "listMediaReorderHandle"),
            key=lambda item: item.mapToScene(QPointF(0, 0)).y(),
        )
        # Drop onto the third row using live delegate geometry instead of a
        # hard-coded pitch that drifts with Theme spacing / fontconfig.
        target = handles[2].mapToScene(
            QPointF(handles[2].width() / 2, handles[2].height() / 2)
        )
        _drag(window, handles[0], target)
        wait_for(app, lambda: [row["tmdb_id"] for row in controller.items] == [2, 3, 1])
        assert window.findChild(QQuickItem, "contentStack").property("depth") == 1
    finally:
        window.close()
        controller.close()
        app.processEvents()


def test_library_drag_autoscrolls_to_cards_outside_initial_view(ordered_factory):
    with ordered_factory.begin() as session:
        for item_id in range(4, 55):
            media = MediaRepository(session).upsert(
                item_id, MediaType.MOVIE, f"Item {item_id}"
            )
            UserMediaRepository(session).set_status(media.id, TrackingStatus.PLANNED)
    controller = MovieLibraryController(
        MovieLibraryService(ordered_factory), images=FakeImages()
    )
    app, engine, window = create_application(
        token_controller=TokenController(store=ExistingTokenStore()),
        movie_library_controller=controller,
    )
    try:
        window.resize(1366, 768)
        window.navigate(1)
        wait_for(app, lambda: len(controller.items) == 54 and not controller.busy)
        grid = window.findChild(QQuickItem, "movieLibraryGrid")
        source_id = controller.items[0]["tmdb_id"]
        handle = _visual(grid.property("currentItem"), "cardDragArea")
        start = handle.mapToScene(QPointF(handle.width() / 2, handle.height() / 2))
        QTest.wheelEvent(window, start, QPoint(0, -120))
        wait_for(app, lambda: grid.property("contentY") > 0)
        assert not grid.property("currentItem").property("reorderDragging")
        grid.setProperty("contentY", 0)
        app.processEvents()
        destination = grid.mapToScene(
            QPointF(grid.property("cellWidth") / 2, grid.height() - 6)
        )
        QTest.mousePress(
            window,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            start.toPoint(),
        )
        for index in range(1, 9):
            QTest.mouseMove(
                window, (start + (destination - start) * (index / 8)).toPoint(), 15
            )
        for _ in range(80):
            QTest.qWait(25)
            if grid.property("contentY") > grid.property("cellHeight") * 2:
                break
        assert grid.property("contentY") > grid.property("cellHeight") * 2
        QTest.mouseRelease(
            window,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            destination.toPoint(),
        )
        wait_for(
            app,
            lambda: (
                not controller.reordering
                and controller.items[0]["tmdb_id"] != source_id
            ),
        )
        assert (
            next(
                i
                for i, row in enumerate(controller.items)
                if row["tmdb_id"] == source_id
            )
            >= 12
        )
        assert window.findChild(QQuickItem, "contentStack").property("depth") == 1
    finally:
        window.close()
        controller.close()
        app.processEvents()


def test_picker_selects_both_types_across_queries_and_adds_once(ordered_factory):
    service = CustomListsService(ordered_factory)
    list_id = service.create("Selection")
    controller = CustomListsController(service, images=FakeImages())
    app, engine, window = create_application(
        token_controller=TokenController(store=ExistingTokenStore()),
        custom_lists_controller=controller,
    )
    try:
        window.navigate(3)
        controller.selectList(list_id)
        wait_for(app, lambda: not controller.busy and len(controller.candidates) == 6)
        window.findChild(QQuickItem, "addMediaToListButton").clicked.emit()
        picker = window.findChild(QObject, "mediaPickerDialog")
        wait_for(app, lambda: picker.property("opened"))
        search = window.findChild(QQuickItem, "listMediaSearchInput")
        search.setProperty("text", "Item 1")
        view = window.findChild(QQuickItem, "mediaPickerCandidates")
        wait_for(app, lambda: view.property("count") == 2)
        wait_for(app, lambda: len(_all_visual(view, "mediaPickerOption")) == 2)
        for kind in ("movie", "tv"):
            row = next(
                item
                for item in _all_visual(view, "mediaPickerOption")
                if _model_data(item)["kind"] == kind
            )
            row.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Space)
        assert picker.property("selectionCount") == 2
        search.setProperty("text", "Item 3")
        app.processEvents()
        assert picker.property("selectionCount") == 2
        window.findChild(QQuickItem, "confirmAddMediaButton").clicked.emit()
        wait_for(app, lambda: not controller.busy and len(controller.items) == 2)
        assert {(row["kind"], row["tmdb_id"]) for row in controller.items} == {
            ("movie", 1),
            ("tv", 1),
        }
        assert len(service.snapshot(list_id)["items"]) == 2
    finally:
        window.close()
        controller.close()
        app.processEvents()


def _all_visual(item, name):
    found = [item] if item.objectName() == name else []
    for child in item.childItems():
        found.extend(_all_visual(child, name))
    return found


def _model_data(item):
    """QML modelData is often a QJSValue under PySide6 — normalize to a mapping."""
    data = item.property("modelData")
    if hasattr(data, "toVariant"):
        data = data.toVariant()
    return data


def test_shutdown_drains_queued_multi_add(ordered_factory):
    QGuiApplication.instance() or QGuiApplication([])
    service = CustomListsService(ordered_factory)
    list_id = service.create("Shutdown")
    controller = CustomListsController(service, images=FakeImages())
    entered, release = Event(), Event()

    def block():
        entered.set()
        assert release.wait(timeout=5)

    blocker = controller._executor.submit(block)
    assert entered.wait(timeout=2)
    controller.addMany(list_id, [{"kind": "movie", "tmdb_id": 1}])
    closer = Thread(target=controller.close)
    closer.start()
    try:
        release.set()
        blocker.result(timeout=2)
        closer.join(timeout=3)
        assert not closer.is_alive()
        assert len(service.snapshot(list_id)["items"]) == 1
    finally:
        release.set()
        closer.join(timeout=3)
