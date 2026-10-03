import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

ComboBox {
    id: control
    implicitHeight: Tokens.Theme.controlHeight
    focusPolicy: Qt.StrongFocus

    contentItem: Label {
        text: control.displayText
        color: Tokens.Theme.textPrimary
        verticalAlignment: Text.AlignVCenter
        leftPadding: Tokens.Theme.spaceSm
        rightPadding: Tokens.Theme.spaceSm
        elide: Text.ElideRight
    }
    background: Rectangle {
        color: Tokens.Theme.surfaceElevated
        radius: Tokens.Theme.radiusSm
        border.color: control.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
        border.width: control.activeFocus ? 2 : 1
    }
    delegate: ItemDelegate {
        width: control.width
        text: modelData.text
        contentItem: Label {
            text: parent.text
            color: Tokens.Theme.textPrimary
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            color: parent.hovered ? Tokens.Theme.hoverSurface
                                  : Tokens.Theme.surfaceElevated
        }
    }
    popup: Popup {
        y: control.height
        width: control.width
        padding: 0
        contentItem: ListView {
            implicitHeight: Math.min(contentHeight, 240)
            model: control.popup.visible ? control.delegateModel : null
        }
        background: Rectangle {
            color: Tokens.Theme.surfaceElevated
            border.color: Tokens.Theme.border
            radius: Tokens.Theme.radiusSm
        }
    }
}
