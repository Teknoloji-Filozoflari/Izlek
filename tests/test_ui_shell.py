"""Exercise the QML shell through its visible navigation controls."""

import os
import subprocess
import sys

from PySide6.QtCore import (
    QObject,
    QPoint,
    QPointF,
    QSettings,
    Qt,
    QTimer,
    QtMsgType,
    qInstallMessageHandler,
)
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.security.token_store import StoredToken
from izlek.ui.controllers.token_controller import TokenController


class ExistingTokenStore:
    def load(self):
        return StoredToken("test-only", "keyring")


def test_sidebar_routes_and_compact_resize(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    warnings = []

    def collect_warning(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous_handler = qInstallMessageHandler(collect_warning)
    try:
        controller = TokenController(store=ExistingTokenStore())
        application, engine, window = create_application(token_controller=controller)
        stack = window.findChild(QQuickItem, "contentStack")
        sidebar = window.findChild(QQuickItem, "sidebar")
        assert window.title() == "İzlek"
        assert (window.width(), window.height()) == (1280, 800)
        assert sidebar.width() == 228

        assert window.minimumWidth() == 800
        assert window.minimumHeight() == 600
        assert window.screen().devicePixelRatio() > 0

        for index, name, title in (
            (1, "navMovies", "Filmler"),
            (2, "navShows", "Diziler"),
            (3, "navLists", "Listeler"),
            (4, "navDiscover", "Keşfet"),
            (5, "navSettings", "Ayarlar"),
            (0, "navHome", "Ana Sayfa"),
        ):
            item = window.findChild(QQuickItem, name)
            assert item.property("iconReady") is True
            center = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
            QTest.mouseClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(int(center.x()), int(center.y())),
            )
            application.processEvents()
            assert window.property("currentIndex") == index
            assert stack.property("currentItem").property("pageTitle") == title

        window.setWidth(850)
        application.processEvents()
        assert window.property("compactSidebar") is True
        assert sidebar.width() == 68
        QTimer.singleShot(0, application.quit)
        assert application.exec() == 0
        settings = QSettings(
            str(tmp_path / "izlek/window.ini"), QSettings.Format.IniFormat
        )
        assert settings.value("window/width", type=int) == 850
        window.close()
        application.processEvents()
        assert not warnings
    finally:
        qInstallMessageHandler(previous_handler)


def test_application_shortcuts_and_escape_close_search(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    controller = TokenController(store=ExistingTokenStore())
    application, engine, window = create_application(token_controller=controller)
    try:
        for key, index in (
            (Qt.Key.Key_2, 1),
            (Qt.Key.Key_3, 2),
            (Qt.Key.Key_4, 3),
            (Qt.Key.Key_5, 4),
            (Qt.Key.Key_Comma, 5),
            (Qt.Key.Key_1, 0),
        ):
            QTest.keyClick(window, key, Qt.KeyboardModifier.ControlModifier)
            QTest.qWait(30)
            assert window.property("currentIndex") == index

        QTest.keyClick(window, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
        QTest.qWait(30)
        search = window.findChild(QObject, "globalSearch")
        assert search.property("opened")
        assert window.findChild(QQuickItem, "globalSearchInput").hasActiveFocus()

        QTest.keyClick(window, Qt.Key.Key_Escape)
        QTest.qWait(30)
        assert not search.property("opened")
    finally:
        window.close()
        application.processEvents()


def test_high_dpi_scale_factor_loads_qml(tmp_path):
    environment = os.environ | {
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "QT_SCALE_FACTOR": "2",
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
    }
    script = """
from izlek.app import create_application
from izlek.security.token_store import StoredToken
from izlek.ui.controllers.token_controller import TokenController

class Store:
    def load(self):
        return StoredToken('test-only', 'keyring')

token = TokenController(store=Store())
app, engine, window = create_application(token_controller=token)
assert engine.rootObjects()
assert window.screen().devicePixelRatio() >= 2
window.close()
app.processEvents()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
