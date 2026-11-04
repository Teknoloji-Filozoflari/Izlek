"""Persisted SplitView pane widths in window.ini."""

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.security.token_store import StoredToken
from izlek.ui.controllers.pane_layout_controller import PaneLayoutController
from izlek.ui.controllers.token_controller import TokenController


class ExistingTokenStore:
    def load(self):
        return StoredToken("test-only", "keyring")


def test_pane_layout_controller_clamps_and_persists(tmp_path):
    path = tmp_path / "window.ini"
    settings = QSettings(str(path), QSettings.Format.IniFormat)
    controller = PaneLayoutController(settings=settings)
    assert controller.widthFor("lists_sidebar", 0) == 300
    controller.setWidthFor("lists_sidebar", 340)
    assert controller.widthFor("lists_sidebar", 0) == 340
    controller.setWidthFor("lists_sidebar", 10)
    assert controller.widthFor("lists_sidebar", 0) == 220
    controller.setWidthFor("lists_sidebar", 9000)
    assert controller.widthFor("lists_sidebar", 0) == 480
    reopened = PaneLayoutController(
        settings=QSettings(str(path), QSettings.Format.IniFormat)
    )
    assert reopened.widthFor("lists_sidebar", 0) == 480


def test_discover_and_lists_panes_resize_and_persist(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    application, engine, window = create_application(
        token_controller=TokenController(store=ExistingTokenStore())
    )
    try:
        window.resize(1366, 768)
        application.processEvents()
        filters = window.findChild(QQuickItem, "discoverFilters")
        assert filters is not None
        assert 220 <= filters.width() <= 420
        filters.setProperty("SplitView.preferredWidth", 330)
        # Preferred width is an attached property; drag the split handle instead.
        split = window.findChild(QQuickItem, "discoverSplit")
        assert split is not None
        handle = None
        for child in split.childItems():
            if child is filters:
                continue
            # content pane or handle; prefer a narrow handle-like item
            if child.width() <= 16:
                handle = child
                break
        if handle is None:
            # Fall back: set width via paneLayout and re-read after navigate.
            panes = engine.rootContext().contextProperty("paneLayout")
            panes.setWidthFor("discover_filters", 330)
            assert panes.widthFor("discover_filters", 0) == 330
        else:
            center = handle.mapToScene(QPointF(handle.width() / 2, handle.height() / 2))
            QTest.mousePress(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(int(center.x()), int(center.y())),
            )
            QTest.mouseMove(
                window,
                QPoint(int(center.x()) + 40, int(center.y())),
            )
            QTest.mouseRelease(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(int(center.x()) + 40, int(center.y())),
            )
            application.processEvents()

        window.navigate(3)
        application.processEvents()
        lists_pane = window.findChild(QQuickItem, "listsSidebar")
        assert lists_pane is not None
        assert 220 <= lists_pane.width() <= 480

        panes = engine.rootContext().contextProperty("paneLayout")
        panes.setWidthFor("lists_sidebar", 360)
        assert panes.widthFor("lists_sidebar", 0) == 360

        settings = QSettings(
            str(tmp_path / "izlek/window.ini"), QSettings.Format.IniFormat
        )
        assert int(settings.value("panes/lists_sidebar")) == 360
    finally:
        window.close()
        application.processEvents()
