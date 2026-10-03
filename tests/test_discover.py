"""Discover controller and QML page use score-ranked TMDb Discover endpoints."""

from concurrent.futures import Future
from pathlib import Path

from PySide6.QtCore import Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.security.token_store import StoredToken
from izlek.tmdb.models import MovieSearchResults, TvSearchResults
from izlek.ui.controllers.discover_controller import DiscoverController
from izlek.ui.controllers.token_controller import TokenController


class _Images:
    def poster(self, path, size="grid"):
        future = Future()
        future.set_result(
            Path(__file__).resolve().parents[1]
            / "src/izlek/resources/images/poster-placeholder.svg"
        )
        return future


class _DiscoverClient:
    def __init__(self):
        self.calls = []

    def discover_movie(self, **filters):
        self.calls.append(("movie", filters))
        return MovieSearchResults.model_validate(
            {
                "page": filters["page"],
                "total_pages": 2,
                "total_results": 2,
                "results": [
                    {
                        "id": 10,
                        "title": "Türkçe Ad",
                        "original_title": "Movie Original",
                        "release_date": "2024-01-01",
                        "vote_average": 8.4,
                    }
                ],
            }
        )

    def discover_tv(self, **filters):
        self.calls.append(("tv", filters))
        return TvSearchResults.model_validate(
            {
                "page": filters["page"],
                "total_pages": 2,
                "total_results": 2,
                "results": [
                    {
                        "id": 20,
                        "name": "Türkçe Dizi",
                        "original_name": "Show Original",
                        "first_air_date": "2021-01-01",
                        "vote_average": 8.1,
                    }
                ],
            }
        )


class _Store:
    def load(self):
        return StoredToken("test-only", "keyring")


def _wait_for(application, predicate):
    for _ in range(100):
        application.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Keşfet sonuçları yüklenmedi")


def test_discover_controller_filters_scores_and_paginates(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    application = QGuiApplication.instance() or QGuiApplication([])
    client = _DiscoverClient()
    controller = DiscoverController(client=client, images=_Images())
    try:
        controller.applyFilters("tv", "2021", 18, "tr", 75, 90)
        _wait_for(application, lambda: not controller.busy)
        assert controller.items[0]["title"] == "Show Original"
        assert controller.items[0]["progressText"] == "TMDb 8.1"
        assert client.calls[-1] == (
            "tv",
            {
                "page": 1,
                "year": 2021,
                "genre_id": 18,
                "country": "TR",
                "min_score": 7.5,
                "max_score": 9.0,
                "min_vote_count": 100,
            },
        )
        controller.goToPage(2)
        _wait_for(application, lambda: not controller.busy and controller.page == 2)
        assert client.calls[-1][1]["page"] == 2
    finally:
        controller.close()


def test_discover_page_filters_and_dense_results(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    application = QGuiApplication.instance() or QGuiApplication([])
    client = _DiscoverClient()
    discover = DiscoverController(client=client, images=_Images())
    warnings = []

    def collect(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous = qInstallMessageHandler(collect)
    application, engine, window = create_application(
        token_controller=TokenController(store=_Store()),
        discover_controller=discover,
    )
    try:
        window.navigate(4)
        _wait_for(application, lambda: not discover.busy and bool(discover.items))
        filters = window.findChild(QQuickItem, "discoverFilters")
        grid = window.findChild(QQuickItem, "discoverResults")
        next_button = window.findChild(QQuickItem, "discoverNext")
        assert all(item is not None for item in (filters, grid, next_button))
        assert grid.property("columns") >= 4
        for width, height in ((1366, 768), (1920, 1080)):
            window.resize(width, height)
            application.processEvents()
            assert filters.width() > 200 and grid.width() > 0
        next_button.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        _wait_for(application, lambda: not discover.busy and discover.page == 2)
        assert not warnings
    finally:
        window.close()
        discover.close()
        application.processEvents()
        qInstallMessageHandler(previous)
