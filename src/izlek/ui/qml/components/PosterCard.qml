import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

Button {
    id: card
    property url posterSource
    property string mediaTitle: ""
    property string year: ""
    property string status: ""
    property real progress: -1
    property string progressText: ""
    property bool favorite: false
    property bool favoriteEnabled: false
    readonly property bool posterReady: poster.status === Image.Ready
    readonly property string statusLabel: status === "PLANNED" ? "İzlenecek"
                                          : status === "WATCHING" ? "İzleniyor"
                                          : status === "WATCHED" ? "İzlendi" : ""
    signal activated()
    signal favoriteToggled(bool favorite)

    implicitWidth: Tokens.Theme.cardWidth
    implicitHeight: Tokens.Theme.cardHeight
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: mediaTitle + (year.length ? ", " + year : "")
                     + (statusLabel.length ? ", " + statusLabel : "")
                     + (progressText.length ? ", " + progressText : "")
    onClicked: activated()
    Keys.onReturnPressed: function(event) { card.activated(); event.accepted = true }
    Keys.onEnterPressed: function(event) { card.activated(); event.accepted = true }

    contentItem: Column {
        spacing: 0

        Rectangle {
            id: posterFrame
            width: parent.width
            height: Math.round(width * 1.5)
            radius: Tokens.Theme.radiusMd
            color: Tokens.Theme.surfaceElevated
            clip: true

            Image {
                id: poster
                anchors.fill: parent
                source: card.posterSource
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                sourceSize.width: Math.round(posterFrame.width * Screen.devicePixelRatio)
                sourceSize.height: Math.round(posterFrame.height * Screen.devicePixelRatio)
            }

            Skeleton {
                anchors.fill: parent
                visible: poster.status === Image.Loading
            }

            Column {
                visible: poster.status !== Image.Loading && !card.posterReady
                anchors.centerIn: parent
                spacing: Tokens.Theme.spaceSm
                Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "▣"
                    color: Tokens.Theme.textMuted
                    font.pixelSize: Tokens.Theme.textStat
                }
                Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Poster yok"
                    color: Tokens.Theme.textMuted
                    font.pixelSize: Tokens.Theme.textSmall
                }
            }

            Badge {
                visible: card.statusLabel.length > 0
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.margins: Tokens.Theme.spaceSm
                text: card.statusLabel
                tone: card.status === "WATCHING" ? "accent"
                      : card.status === "WATCHED" ? "success" : "neutral"
            }
            FavoriteButton {
                objectName: "cardFavorite"
                visible: card.favoriteEnabled
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: Tokens.Theme.spaceSm
                checked: card.favorite
                onToggledFavorite: function(value) { card.favoriteToggled(value) }
            }
        }

        Item {
            width: parent.width
            height: Math.max(0, card.height - posterFrame.height)

            Label {
                id: titleLabel
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Tokens.Theme.spaceSm
                text: card.mediaTitle
                color: Tokens.Theme.textPrimary
                font.pixelSize: Tokens.Theme.textBody
                font.weight: Tokens.Theme.weightDemiBold
                maximumLineCount: 2
                wrapMode: Text.WordWrap
                elide: Text.ElideRight
            }
            Label {
                id: metaLabel
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: titleLabel.bottom
                anchors.topMargin: 2
                anchors.leftMargin: Tokens.Theme.spaceSm
                anchors.rightMargin: Tokens.Theme.spaceSm
                text: card.progressText.length
                    ? (card.year.length ? card.year + " · " : "") + card.progressText
                    : card.year
                color: Tokens.Theme.textSecondary
                font.pixelSize: Tokens.Theme.textSmall
                elide: Text.ElideRight
            }
            Rectangle {
                visible: card.progress >= 0
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: Tokens.Theme.spaceSm
                height: 4
                radius: 2
                color: Tokens.Theme.border
                Rectangle {
                    width: parent.width * Math.max(0, Math.min(1, card.progress))
                    height: parent.height
                    radius: parent.radius
                    color: Tokens.Theme.accent
                }
            }
        }
    }

    background: Rectangle {
        color: card.hovered ? Tokens.Theme.surfaceElevated : Tokens.Theme.surface
        radius: Tokens.Theme.radiusMd
        border.width: card.activeFocus ? 2 : card.hovered ? 1 : 0
        border.color: card.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
    }
}
