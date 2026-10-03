import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

Button {
    id: control
    property url iconSource
    property string toolTipText: ""
    implicitWidth: Tokens.Theme.controlHeight
    implicitHeight: Tokens.Theme.controlHeight
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: toolTipText
    ToolTip.visible: hovered && toolTipText.length > 0
    ToolTip.text: toolTipText
    ToolTip.delay: 500

    contentItem: Image {
        source: control.iconSource
        sourceSize.width: 20
        sourceSize.height: 20
        fillMode: Image.PreserveAspectFit
        opacity: control.enabled ? 1 : 0.45
    }
    background: Rectangle {
        radius: Tokens.Theme.radiusSm
        color: control.down ? Tokens.Theme.hoverSurface
             : control.hovered ? Tokens.Theme.surfaceElevated : "transparent"
        border.width: control.activeFocus ? 2 : 0
        border.color: Tokens.Theme.accent
    }
}
