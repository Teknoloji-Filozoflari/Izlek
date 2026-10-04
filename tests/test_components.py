"""Exercise reusable QML controls in the offline development gallery."""

from PySide6.QtCore import (
    QObject,
    QPoint,
    QPointF,
    Qt,
    QtMsgType,
    qInstallMessageHandler,
)
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application


def _click_center(window, item):
    center = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    QTest.mouseClick(
        window,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(int(center.x()), int(center.y())),
    )


def test_gallery_layout_and_keyboard_controls(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    warnings = []

    def collect_warning(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous_handler = qInstallMessageHandler(collect_warning)
    try:
        application, engine, window = create_application(gallery=True)
        grid = window.findChild(QQuickItem, "galleryGrid")
        window.resize(1366, 768)
        application.processEvents()
        assert grid.property("columns") == 7
        assert grid.property("count") == 18

        activated = []
        grid.mediaActivated.connect(lambda media: activated.append(media))
        card = grid.property("currentItem")
        card.forceActiveFocus()
        assert card.hasActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Return)
        application.processEvents()
        media = activated[0]
        if hasattr(media, "toVariant"):
            media = media.toVariant()
        assert media["title"] == "Night Line"
        toast = window.findChild(QObject, "galleryToast")
        assert toast.property("message") == "Night Line seçildi"
        QTest.keyClick(window, Qt.Key.Key_Space)
        application.processEvents()
        assert len(activated) == 2

        search = window.findChild(QQuickItem, "gallerySearch")
        search.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_T)
        assert search.property("text") == "t"
        _click_center(window, search.findChild(QQuickItem, "searchClear"))
        assert search.property("text") == ""

        favorite = window.findChild(QQuickItem, "galleryFavorite")
        _click_center(window, favorite)
        assert favorite.property("checked") is True

        status = window.findChild(QQuickItem, "galleryStatus")
        status.setProperty("status", "WATCHED")
        assert status.property("currentIndex") == 2
        status.setProperty("status", "PLANNED")
        assert status.property("currentIndex") == 0
        right_segment = status.mapToScene(
            QPointF(status.width() * 5 / 6, status.height() / 2)
        )
        QTest.mouseClick(
            window,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(int(right_segment.x()), int(right_segment.y())),
        )
        assert status.property("status") == "WATCHED"

        dialog = window.findChild(QObject, "galleryDialog")
        dialog.open()
        application.processEvents()
        assert dialog.property("visible") is True
        dialog.close()

        window.resize(1920, 1080)
        application.processEvents()
        assert grid.property("columns") == 9
        assert grid.width() >= 1600
        window.close()
        application.processEvents()
        assert not warnings
    finally:
        qInstallMessageHandler(previous_handler)
