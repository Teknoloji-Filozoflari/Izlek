import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

Button {
    id: control
    signal toggledFavorite(bool favorite)
    checkable: true
    implicitWidth: Tokens.Theme.controlHeight
    implicitHeight: Tokens.Theme.controlHeight
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: checked ? "Favorilerden çıkar" : "Favorilere ekle"
    onClicked: toggledFavorite(checked)

    contentItem: Label {
        text: control.checked ? "♥" : "♡"
        color: control.checked ? Tokens.Theme.accent : Tokens.Theme.textSecondary
        font.pixelSize: Tokens.Theme.textHeading
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: Tokens.Theme.radiusSm
        color: control.hovered ? Tokens.Theme.hoverSurface : Tokens.Theme.surfaceElevated
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
    }
}
