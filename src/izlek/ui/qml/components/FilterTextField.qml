import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

TextField {
    id: field
    implicitHeight: Tokens.Theme.controlHeight
    color: Tokens.Theme.textPrimary
    placeholderTextColor: Tokens.Theme.textMuted
    selectionColor: Tokens.Theme.accentSurface
    selectedTextColor: Tokens.Theme.textPrimary
    focusPolicy: Qt.StrongFocus
    leftPadding: Tokens.Theme.spaceSm
    rightPadding: Tokens.Theme.spaceSm
    background: Rectangle {
        color: Tokens.Theme.surfaceElevated
        radius: Tokens.Theme.radiusSm
        border.color: field.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
        border.width: field.activeFocus ? 2 : 1
    }
}
