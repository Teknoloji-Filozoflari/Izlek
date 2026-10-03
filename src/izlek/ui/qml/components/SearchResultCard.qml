import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Button {
    id: card
    property var media: ({})
    signal activated(string kind, int itemId)
    width: parent ? parent.width : 540
    implicitHeight: 86
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: (media.title || "") + ", " + (media.mediaType === "movie" ? "Film" : "Dizi")
    onClicked: activated(media.mediaType, media.id)

    contentItem: RowLayout {
        spacing: Tokens.Theme.spaceMd
        Image {
            Layout.preferredWidth: 48
            Layout.preferredHeight: 72
            source: card.media.poster || ""
            asynchronous: true
            fillMode: Image.PreserveAspectCrop
            sourceSize.width: Math.round(48 * Screen.devicePixelRatio)
            sourceSize.height: Math.round(72 * Screen.devicePixelRatio)
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Tokens.Theme.spaceXs
            Label {
                Layout.fillWidth: true
                text: card.media.title || ""
                color: Tokens.Theme.textPrimary
                font.pixelSize: Tokens.Theme.textBody
                font.weight: Tokens.Theme.weightDemiBold
                elide: Text.ElideRight
            }
            Label {
                text: (card.media.year || "Yıl bilinmiyor") + " · "
                      + (card.media.mediaType === "movie" ? "Film" : "Dizi")
                color: Tokens.Theme.textSecondary
                font.pixelSize: Tokens.Theme.textSmall
            }
        }
    }

    background: Rectangle {
        color: card.hovered || card.activeFocus
               ? Tokens.Theme.hoverSurface : Tokens.Theme.surfaceElevated
        radius: Tokens.Theme.radiusSm
        border.width: card.activeFocus ? 2 : 1
        border.color: card.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
    }
}
