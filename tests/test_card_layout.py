"""Long captions and quick actions stay usable in both card densities."""

from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QtMsgType, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest


def _visual_children(item, name):
    found = [item] if item.objectName() == name else []
    for child in item.childItems():
        found.extend(_visual_children(child, name))
    return found


def test_long_card_titles_and_quick_actions_in_both_densities():
    app = QGuiApplication.instance() or QGuiApplication([])
    warnings = []

    def collect(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous = qInstallMessageHandler(collect)
    engine = QQmlApplicationEngine()
    qml = Path(__file__).resolve().parents[1] / "src/izlek/ui/qml/LayoutTest.qml"
    engine.loadData(br'''
import QtQuick
import QtQuick.Controls
import "components"
ApplicationWindow {
    visible: true
    width: 850
    height: 650
    QtObject {
        id: actions
        property var states: ({})
        property int calls: 0
        function add(media) { calls++ }
    }
    property alias addCalls: actions.calls
    MediaGrid {
        id: mediaGrid
        objectName: "layoutGrid"
        anchors.fill: parent
        anchors.margins: 24
        quickLibraryController: actions
        items: [
            { id: 1, mediaType: "movie",
              title: "Northbound: A Journey Beyond the Mountains",
              year: "2024", score: 8.2 },
            { id: 2, mediaType: "tv", title: "Orbit", year: "2025",
              status: "WATCHING", progress: 0.5,
              progressText: "4 / 8 b\u00f6l\u00fcm" }
        ]
    }
}
''', QUrl.fromLocalFile(str(qml)))
    try:
        assert engine.rootObjects()
        window = engine.rootObjects()[0]
        grid = window.findChild(QQuickItem, "layoutGrid")
        activated = []
        grid.mediaActivated.connect(activated.append)
        for width in (850, 1366, 1920):
            window.resize(width, 768)
            for compact in (False, True):
                grid.setProperty("compact", compact)
                app.processEvents()
                QTest.qWait(30)
                card = grid.property("currentItem")
                titles = _visual_children(grid, "cardTitle")
                assert len(titles) == 2
                long_title = next(
                    item for item in titles if item.property("text").startswith("North")
                )
                assert long_title.property("lineCount") == 2
                assert long_title.property("contentHeight") <= long_title.height()
                metas = _visual_children(grid, "cardMeta")
                # One- and two-line titles reserve the same caption baseline.
                assert abs(metas[0].mapToScene(QPointF()).y()
                           - metas[1].mapToScene(QPointF()).y()) < 1
                title = _visual_children(card, "cardTitle")[0]
                meta = _visual_children(card, "cardMeta")[0]
                button = _visual_children(card, "quickLibraryAdd")[0]
                assert title.y() + title.height() <= meta.y()
                assert meta.mapToItem(card, QPointF(0, meta.height())).y() <= button.y()
                assert button.y() + button.height() <= card.height()
                assert button.x() >= 0 and button.x() + button.width() <= card.width()
                button.forceActiveFocus()
                QTest.keyClick(window, Qt.Key.Key_Space)
                app.processEvents()
                assert not activated
        assert window.property("addCalls") == 6
        assert not warnings
    finally:
        if engine.rootObjects():
            engine.rootObjects()[0].close()
        app.processEvents()
        qInstallMessageHandler(previous)
