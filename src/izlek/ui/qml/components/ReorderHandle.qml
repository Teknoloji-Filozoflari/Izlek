import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

Item {
    id: handle
    property string label: ""
    property bool showHandle: true
    property url previewSource
    readonly property bool hasPreview: previewSource.toString().length > 0
    readonly property bool dragging: pointer.dragging
    property point cursorPosition: Qt.point(0, 0)
    property point scenePosition: Qt.point(0, 0)
    signal moved(point scenePosition)
    signal dropped(point scenePosition)
    signal tapped()
    signal pressStarted()
    implicitWidth: 28
    implicitHeight: Tokens.Theme.controlHeight
    Accessible.name: label + " sırasını değiştir"
    Rectangle {
        visible: handle.showHandle
        anchors.fill: parent
        radius: Tokens.Theme.radiusSm
        color: pointer.containsMouse || handle.dragging
               ? Tokens.Theme.hoverSurface : Tokens.Theme.surfaceElevated
        border.color: handle.dragging ? Tokens.Theme.accent : Tokens.Theme.border
        Text {
            anchors.centerIn: parent
            text: "⠿"
            color: Tokens.Theme.textSecondary
            font.pixelSize: Tokens.Theme.textBrand
        }
    }
    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        preventStealing: true
        acceptedButtons: Qt.LeftButton
        property bool dragging: false
        property bool draggedDuringPress: false
        property point startPoint
        cursorShape: dragging ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        onPressed: function(mouse) {
            draggedDuringPress = false
            startPoint = Qt.point(mouse.x, mouse.y)
            handle.pressStarted()
        }
        onPositionChanged: function(mouse) {
            if (!pressed) return
            if (!dragging && Math.hypot(mouse.x - startPoint.x, mouse.y - startPoint.y)
                    >= Qt.styleHints.startDragDistance)
                dragging = true
            if (dragging) draggedDuringPress = true
            if (dragging) {
                handle.cursorPosition = handle.mapToItem(Overlay.overlay, mouse.x, mouse.y)
                handle.scenePosition = handle.mapToItem(null, mouse.x, mouse.y)
                handle.moved(handle.scenePosition)
            }
        }
        onReleased: function(mouse) {
            if (dragging) handle.dropped(handle.mapToItem(null, mouse.x, mouse.y))
            dragging = false
        }
        onCanceled: dragging = false
        onClicked: if (!draggedDuringPress) handle.tapped()
    }
    Rectangle {
        parent: Overlay.overlay
        visible: handle.dragging
        x: handle.cursorPosition.x + Tokens.Theme.spaceSm
        y: handle.cursorPosition.y + Tokens.Theme.spaceSm
        width: handle.hasPreview ? 112 : Math.min(220, dragLabel.implicitWidth + 2 * Tokens.Theme.spaceMd)
        height: handle.hasPreview ? preview.implicitHeight + 2 * Tokens.Theme.spaceSm : Tokens.Theme.controlHeight
        color: Tokens.Theme.accentSurface
        border.color: Tokens.Theme.accent
        radius: Tokens.Theme.radiusSm
        z: 100
        Column {
            id: preview
            anchors.centerIn: parent
            width: parent.width - 2 * Tokens.Theme.spaceSm
            spacing: Tokens.Theme.spaceXs
            Image {
                visible: handle.hasPreview
                width: parent.width
                height: width * 1.5
                source: handle.previewSource
                sourceSize.width: 112
                fillMode: Image.PreserveAspectFit
            }
            Label {
                id: dragLabel
                width: parent.width
                text: handle.label
                color: Tokens.Theme.textPrimary
                font.pixelSize: Tokens.Theme.textSmall
                maximumLineCount: handle.hasPreview ? 2 : 1
                wrapMode: handle.hasPreview ? Text.WordWrap : Text.NoWrap
                elide: Text.ElideRight
            }
        }
    }
    ToolTip.visible: handle.showHandle && pointer.containsMouse && !dragging
    ToolTip.text: "Sürükleyerek sırala"
}
