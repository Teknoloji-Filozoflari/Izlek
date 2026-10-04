"""Dashboard empty-state and quick-entry behavior."""

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.security.token_store import StoredToken
from izlek.ui.controllers.token_controller import TokenController


class _Store:
    def load(self):
        return StoredToken("test-only", "keyring")


def _wait_for(application, predicate):
    for _ in range(100):
        application.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Dashboard hazır olmadı")


def test_statistics_without_tracking_sections_and_home_search(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    application = QGuiApplication.instance() or QGuiApplication([])
    application, engine, window = create_application(
        token_controller=TokenController(store=_Store())
    )
    try:
        assert window.findChild(QQuickItem, "discoverFilters") is not None
        assert window.findChild(QQuickItem, "dashboardSearch") is not None
        window.navigate(4)

        assert window.findChild(QQuickItem, "dashboardStats") is not None
        for name in ("dashboardMovies", "dashboardShows", "dashboardFavorites",
                     "allFavoritesButton"):
            assert window.findChild(QQuickItem, name) is None

        window.navigate(0)
        QTest.qWait(300)
        current_page = window.findChild(QQuickItem, "contentStack").property(
            "currentItem"
        )
        search = current_page.findChild(QQuickItem, "dashboardSearch")
        search.forceActiveFocus()
        application.processEvents()
        assert not window.findChild(QObject, "globalSearch").property("visible")
        QTest.keyClick(window, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
        _wait_for(application, lambda: search.hasActiveFocus())
        assert not window.findChild(QObject, "globalSearch").property("visible")
    finally:
        window.close()
        application.processEvents()
