import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Dialog {
    id: dialog
    property string message: ""
    property string confirmText: "Onayla"
    property string cancelText: "Vazgeç"
    property Component bodyComponent
    signal confirmed()

    modal: true
    focus: true
    width: Math.min(440, parent ? parent.width - 2 * Tokens.Theme.spaceLg : 440)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: Tokens.Theme.spaceLg
    closePolicy: Popup.CloseOnEscape
    onOpened: cancelButton.forceActiveFocus()
    onAccepted: confirmed()
    Overlay.modal: Rectangle { color: Tokens.Theme.scrim }

    header: Label {
        text: dialog.title
        color: Tokens.Theme.textPrimary
        font.pixelSize: Tokens.Theme.textEmpty
        font.weight: Tokens.Theme.weightDemiBold
        padding: Tokens.Theme.spaceLg
    }

    contentItem: ColumnLayout {
        spacing: Tokens.Theme.spaceMd
        Label {
            visible: dialog.message.length > 0
            text: dialog.message
            color: Tokens.Theme.textSecondary
            font.pixelSize: Tokens.Theme.textBody
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Loader {
            active: dialog.bodyComponent !== null
            sourceComponent: dialog.bodyComponent
            Layout.fillWidth: true
        }
    }

    footer: RowLayout {
        spacing: Tokens.Theme.spaceSm
        Item { Layout.fillWidth: true }
        IzlekButton {
            id: cancelButton
            text: dialog.cancelText
            variant: "secondary"
            onClicked: dialog.reject()
        }
        IzlekButton {
            text: dialog.confirmText
            onClicked: dialog.accept()
        }
    }

    background: Rectangle {
        color: Tokens.Theme.surfaceElevated
        radius: Tokens.Theme.radiusMd
        border.color: Tokens.Theme.border
    }
}
