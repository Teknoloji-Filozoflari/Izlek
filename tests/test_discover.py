"""Discover controller and QML page use score-ranked TMDb Discover endpoints."""

from concurrent.futures import Future
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlExpression
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


def test_discover_limits_available_pages_and_discards_old_token_response(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    QGuiApplication.instance() or QGuiApplication([])
    controller = DiscoverController(
        store=_Store(), client=_DiscoverClient(), images=_Images()
    )
    try:
        controller._apply_loaded(0, [], 1, 2000, "")
        assert controller.totalPages == 500
        generation = controller._generation
        controller.refresh_token()
        controller._apply_loaded(generation, [{"title": "Old result"}], 1, 1, "")
        assert controller.items == []
        assert not controller.busy
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
        assert window.property("currentIndex") == 0
        assert (
            window.findChild(QQuickItem, "contentStack")
            .property("currentItem")
            .property("pageTitle")
            == "Ana Sayfa"
        )
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

        def labels(item):
            found = [item] if item.objectName() == "filterOptionLabel" else []
            for child in item.childItems():
                found.extend(labels(child))
            return found

        for name in ("discoverMedia", "discoverGenre", "discoverCountry"):
            combo = window.findChild(QQuickItem, name)
            combo.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Space)
            _wait_for(
                application,
                lambda combo=combo: QQmlExpression(
                    engine.rootContext(), combo, "popup.opened"
                ).evaluate()[0],
            )
            content = QQmlExpression(
                engine.rootContext(), combo, "popup.contentItem"
            ).evaluate()[0]
            options = labels(content)
            assert options and all(label.property("text") for label in options)
            assert (
                options[0].property("text")
                == {
                    "discoverMedia": "Film",
                    "discoverGenre": "Tüm türler",
                    "discoverCountry": "Tüm ülkeler",
                }[name]
            )
            assert all(
                label.property("text") == label.property("text").strip()
                for label in options
            )
            assert content.property("contentY") == 0
            assert options[0].parentItem().y() == 0
            assert options[0].parentItem().height() == 42
            for label in options:
                if (
                    label.parentItem().y() + label.parentItem().height()
                    > content.height()
                ):
                    continue
                center = label.mapToScene(
                    QPointF(label.width() / 2, label.height() / 2)
                )
                QTest.mouseMove(window, center.toPoint())
                QTest.qWait(50)
                assert all(option.isVisible() for option in options)
                assert label.property("color").lightness() > 150
                assert label.property("text") != "undefined"
            QTest.keyClick(window, Qt.Key.Key_Escape)
            _wait_for(
                application,
                lambda combo=combo: (
                    not QQmlExpression(
                        engine.rootContext(), combo, "popup.visible"
                    ).evaluate()[0]
                ),
            )
        next_button.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        _wait_for(application, lambda: not discover.busy and discover.page == 2)
        assert not warnings
    finally:
        window.close()
        discover.close()
        application.processEvents()
        qInstallMessageHandler(previous)


@pytest.mark.parametrize("locale", ["en_US", "tr_TR"])
def test_score_apply_preserves_decimal_value_and_clear_resets(locale):
    client = _DiscoverClient()
    discover = DiscoverController(client=client, images=_Images())
    application, engine, window = create_application(
        token_controller=TokenController(store=_Store()), discover_controller=discover
    )
    try:
        window.resize(1366, 768)
        _wait_for(application, lambda: not discover.busy)
        minimum = window.findChild(QQuickItem, "discoverMinScore")
        maximum = window.findChild(QQuickItem, "discoverMaxScore")
        for score in (minimum, maximum):
            QQmlExpression(
                engine.rootContext(), score, f"locale = Qt.locale('{locale}')"
            ).evaluate()
        for _ in range(15):
            point = minimum.mapToScene(
                QPointF(minimum.width() - 21, minimum.height() / 2)
            )
            QTest.mouseClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                point.toPoint(),
            )
        for _ in range(3):
            point = maximum.mapToScene(QPointF(21, maximum.height() / 2))
            QTest.mouseClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                point.toPoint(),
            )
        assert minimum.property("value") == 75
        assert maximum.property("value") == 85
        minimum.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Up)
        assert minimum.property("value") == 80
        QTest.keyClick(window, Qt.Key.Key_Down)
        assert minimum.property("value") == 75
        for _ in range(2):
            apply = window.findChild(QQuickItem, "applyDiscoverFilters")
            point = apply.mapToScene(QPointF(apply.width() / 2, apply.height() / 2))
            QTest.mouseClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                point.toPoint(),
            )
            _wait_for(application, lambda: not discover.busy)
            assert minimum.property("value") == 75
            assert maximum.property("value") == 85
            assert client.calls[-1][1]["min_score"] == 7.5
            assert client.calls[-1][1]["max_score"] == 8.5
        clear = window.findChild(QQuickItem, "clearDiscoverFilters")
        clear.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        _wait_for(application, lambda: not discover.busy)
        assert minimum.property("value") == 0
        assert maximum.property("value") == 100
    finally:
        window.close()
        discover.close()
        application.processEvents()
