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


def test_empty_dashboard_search_and_quick_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    application = QGuiApplication.instance() or QGuiApplication([])
    application, engine, window = create_application(
        token_controller=TokenController(store=_Store())
    )
    try:
        empty = window.findChild(QQuickItem, "emptyDashboard")
        _wait_for(application, lambda: empty.isVisible())
        message = window.findChild(QQuickItem, "emptyDashboardMessage")
        assert "Film veya dizi arayarak" in message.property("text")

        movies = window.findChild(QQuickItem, "dashboardMovies")
        movies.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        _wait_for(application, lambda: window.property("currentIndex") == 1)

        window.navigate(0)
        shows = window.findChild(QQuickItem, "dashboardShows")
        shows.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        _wait_for(application, lambda: window.property("currentIndex") == 2)

        window.navigate(0)
        search = window.findChild(QQuickItem, "dashboardSearch")
        search.forceActiveFocus()
        _wait_for(
            application,
            lambda: window.findChild(QObject, "globalSearch").property("opened"),
        )
    finally:
        window.close()
        application.processEvents()
