import QtQuick
import QtQuick.Controls
import QtQuick.Templates as T
import "../theme" as Tokens

T.ComboBox {
    id: control
    implicitHeight: Tokens.Theme.controlHeight
    implicitWidth: Math.max(120, implicitContentWidth + leftPadding + rightPadding)
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    font.pixelSize: Tokens.Theme.textBody
    leftPadding: Tokens.Theme.spaceSm
    rightPadding: Tokens.Theme.controlHeight

    contentItem: Text {
        text: control.displayText.trim()
        color: Tokens.Theme.textPrimary
        font: control.font
        z: 1
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        color: Tokens.Theme.surfaceElevated
        radius: Tokens.Theme.radiusSm
        border.color: control.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
        border.width: control.activeFocus ? 2 : 1
    }
    indicator: Text {
        x: control.width - width - Tokens.Theme.spaceSm
        y: (control.height - height) / 2
        text: "▾"
        color: Tokens.Theme.textMuted
        font.pixelSize: Tokens.Theme.textBody
    }
    delegate: T.ItemDelegate {
        id: option
        required property int index
        required property var modelData
        hoverEnabled: true
        width: control.width
        implicitHeight: Tokens.Theme.controlHeight
        height: Tokens.Theme.controlHeight
        leftPadding: Tokens.Theme.spaceSm
        rightPadding: Tokens.Theme.spaceSm
        topPadding: 0
        bottomPadding: 0
        text: (control.textRole ? String(modelData[control.textRole]) : String(modelData)).trim()
        highlighted: control.highlightedIndex === index
        contentItem: Text {
            objectName: "filterOptionLabel"
            text: option.text
            color: Tokens.Theme.textPrimary
            font: control.font
            z: 1
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            z: 0
            color: option.hovered || option.highlighted ? Tokens.Theme.hoverSurface
                                  : Tokens.Theme.surfaceElevated
        }
    }
    popup: T.Popup {
        objectName: control.objectName + "Popup"
        focus: true
        font: control.font
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        y: control.height
        width: control.width
        height: contentItem.implicitHeight + 2 * padding
        padding: 1
        topInset: 0
        bottomInset: 0
        onOpened: {
            optionsView.forceLayout()
            optionsView.positionViewAtBeginning()
        }
        contentItem: ListView {
            id: optionsView
            implicitHeight: Math.min(count * Tokens.Theme.controlHeight, 240)
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            highlightMoveDuration: 0
            boundsBehavior: Flickable.StopAtBounds
            spacing: 0
            clip: true
            ScrollIndicator.vertical: ScrollIndicator {}
        }
        background: Rectangle {
            color: Tokens.Theme.surfaceElevated
            border.color: Tokens.Theme.border
            radius: Tokens.Theme.radiusSm
        }
    }
}
