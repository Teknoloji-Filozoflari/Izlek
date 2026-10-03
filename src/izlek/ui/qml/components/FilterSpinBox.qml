import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

SpinBox {
    id: control
    implicitHeight: Tokens.Theme.controlHeight
    focusPolicy: Qt.StrongFocus
    contentItem: TextInput {
        z: 2
        text: control.textFromValue(control.value, control.locale)
        color: Tokens.Theme.textPrimary
        selectionColor: Tokens.Theme.accentSurface
        selectedTextColor: Tokens.Theme.textPrimary
        font.pixelSize: Tokens.Theme.textBody
        horizontalAlignment: Qt.AlignHCenter
        verticalAlignment: Qt.AlignVCenter
        readOnly: !control.editable
        validator: control.validator
        inputMethodHints: control.inputMethodHints
    }
    background: Rectangle {
        color: Tokens.Theme.surfaceElevated
        radius: Tokens.Theme.radiusSm
        border.color: control.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
        border.width: control.activeFocus ? 2 : 1
    }
    up.indicator: Rectangle {
        x: control.mirrored ? 0 : parent.width - width
        height: parent.height
        width: Tokens.Theme.controlHeight
        radius: Tokens.Theme.radiusSm
        color: control.up.pressed ? Tokens.Theme.hoverSurface : "transparent"
        Label {
            anchors.centerIn: parent
            text: "▲"
            color: control.up.enabled ? Tokens.Theme.textSecondary : Tokens.Theme.textMuted
            font.pixelSize: Tokens.Theme.textSmall
        }
    }
    down.indicator: Rectangle {
        x: control.mirrored ? parent.width - width : 0
        height: parent.height
        width: Tokens.Theme.controlHeight
        radius: Tokens.Theme.radiusSm
        color: control.down.pressed ? Tokens.Theme.hoverSurface : "transparent"
        Label {
            anchors.centerIn: parent
            text: "▼"
            color: control.down.enabled ? Tokens.Theme.textSecondary : Tokens.Theme.textMuted
            font.pixelSize: Tokens.Theme.textSmall
        }
    }
}
