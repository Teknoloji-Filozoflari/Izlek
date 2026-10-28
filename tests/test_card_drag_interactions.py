"""Whole-card dragging preserves ordinary clicks and nested card controls."""

import pytest
from PySide6.QtCore import QPointF, Qt, Slot
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.services.movie_library import MovieLibraryService
from izlek.services.tv_library import TvLibraryService
from izlek.ui.controllers.continue_watching_controller import ContinueWatchingController
from izlek.ui.controllers.movie_library_controller import MovieLibraryController
from izlek.ui.controllers.token_controller import TokenController
from izlek.ui.controllers.tv_library_controller import TvLibraryController
from test_global_search import ExistingTokenStore, FakeImages, wait_for
from test_reordering import _drag, _visual
from test_reordering import ordered_factory as ordered_factory


class _IdleContinueWatching(ContinueWatchingController):
    """Keep Continue Watching chrome idle so TV library layout stays put."""

    @Slot()
    def refresh(self) -> None:
        self._busy = False
        self._error = ""
        self._items = []
        self.changed.emit()
        self.itemsChanged.emit()

    @Slot()
    def refresh_token(self) -> None:
        return


def _click(window, item):
    point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    QTest.mouseClick(
        window,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        point.toPoint(),
    )


def _stable_scene_center(application, area):
    """Wait until the drag hit-box stops moving in scene coordinates.

    TV library can still reflow under offscreen/software Qt; require a short
    stable window before synthesizing the below-threshold click.
    """
    last = None
    stable = 0
    for _ in range(500):
        application.processEvents()
        if area is None or area.width() <= 10 or area.height() <= 10:
            stable = 0
            last = None
            QTest.qWait(10)
            continue
        point = area.mapToScene(QPointF(area.width() / 2, area.height() / 2))
        if (
            last is not None
            and abs(point.x() - last.x()) < 0.5
            and abs(point.y() - last.y()) < 0.5
        ):
            stable += 1
            if stable >= 8:
                return point
        else:
            stable = 0
        last = point
        QTest.qWait(10)
    raise AssertionError("Timed out waiting for stable card geometry")


@pytest.mark.parametrize("kind", ["movie", "tv"])
def test_direct_drag_keeps_click_favorite_selection_and_outside_drop(
    ordered_factory, kind
):
    service_type = MovieLibraryService if kind == "movie" else TvLibraryService
    controller_type = MovieLibraryController if kind == "movie" else TvLibraryController
    controller = controller_type(service_type(ordered_factory), images=FakeImages())
    app, engine, window = create_application(
        token_controller=TokenController(store=ExistingTokenStore()),
        continue_controller=_IdleContinueWatching(),
        **{kind + "_library_controller": controller},
    )
    try:
        window.resize(1366, 768)
        window.navigate(1 if kind == "movie" else 2)
        wait_for(app, lambda: len(controller.items) == 3 and not controller.busy)
        grid = window.findChild(QQuickItem, kind + "LibraryGrid")
        stack = window.findChild(QQuickItem, "contentStack")
        ids = [row["tmdb_id"] for row in controller.items]
        card = grid.property("currentItem")
        area = _visual(card, "cardDragArea")
        assert not _visual(card, "cardReorderHandle")
        # Movement below the platform threshold remains an ordinary click.
        start = _stable_scene_center(app, area)
        QTest.mousePress(
            window,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            start.toPoint(),
        )
        QTest.mouseMove(window, (start + QPointF(1, 1)).toPoint())
        # Re-map release through live geometry in case layout still drifts.
        release = area.mapToScene(
            QPointF(area.width() / 2, area.height() / 2)
        ) + QPointF(1, 1)
        QTest.mouseRelease(
            window,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            release.toPoint(),
        )
        wait_for(app, lambda: stack.property("depth") == 2)
        assert stack.property("currentItem").property("mediaId") == ids[0]
        window.goBack()
        wait_for(app, lambda: not controller.busy)
        card = grid.property("currentItem")
        favorite = _visual(card, "cardFavorite")
        old = controller.items[0]["favorite"]
        _click(window, favorite)
        wait_for(
            app, lambda: controller.items[0]["favorite"] != old and not controller.busy
        )
        assert stack.property("depth") == 1
        assert [row["tmdb_id"] for row in controller.items] == ids
        # Releasing outside the view cancels the reorder without opening a detail.
        card = grid.property("currentItem")
        _drag(window, _visual(card, "cardDragArea"), QPointF(5, 5))
        app.processEvents()
        assert not card.property("reorderDragging")
        assert [row["tmdb_id"] for row in controller.items] == ids
        assert stack.property("depth") == 1
        # Selection mode leaves native card and checkbox actions in charge.
        window.findChild(QQuickItem, "toggleLibrarySelectionButton").clicked.emit()
        card = grid.property("currentItem")
        assert not _visual(card, "cardDragArea").isVisible()
        _click(window, _visual(card, "libraryCardSelection"))
        app.processEvents()
        assert card.property("selected")
        _click(window, _visual(card, "cardTitle"))
        app.processEvents()
        assert not card.property("selected")
        assert stack.property("depth") == 1
        window.findChild(QQuickItem, "toggleLibrarySelectionButton").clicked.emit()
        # Active filters disable drag and preserve the saved complete order.
        controller.applyFilters({"status": "WATCHING"})
        wait_for(app, lambda: not controller.busy)
        card = grid.property("currentItem")
        assert not _visual(card, "cardDragArea").isVisible()
        controller.applyFilters({})
        wait_for(app, lambda: not controller.busy)
        assert [row["tmdb_id"] for row in controller.items] == ids
        # Native keyboard activation still works when direct dragging is enabled.
        card = grid.property("currentItem")
        card.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Return)
        wait_for(app, lambda: stack.property("depth") == 2)
    finally:
        window.close()
        for child in engine.children():
            if callable(getattr(child, "close", None)):
                child.close()
        app.processEvents()
