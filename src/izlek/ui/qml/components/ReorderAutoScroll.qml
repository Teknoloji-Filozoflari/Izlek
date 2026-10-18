import QtQuick

Timer {
    property var view: null
    property bool active: false
    property point scenePosition: Qt.point(0, 0)
    interval: 30
    repeat: true
    running: active && !!view
    onTriggered: {
        var point = view.mapFromItem(null, scenePosition.x, scenePosition.y)
        if (point.x < 0 || point.x > view.width) return
        var step = point.y < 32 ? -12 : point.y > view.height - 32 ? 12 : 0
        view.contentY = Math.max(view.originY,
            Math.min(view.originY + Math.max(0, view.contentHeight - view.height),
                     view.contentY + step))
    }
}
