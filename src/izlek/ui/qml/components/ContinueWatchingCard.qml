import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Rectangle {
    id: card
    objectName: "continueCard"
    property var itemData: ({})
    property var controller: null
    property url posterSource: itemData.poster || ""
    property url backdropSource: itemData.backdrop || ""
    onItemDataChanged: {
        posterSource = itemData.poster || ""
        backdropSource = itemData.backdrop || ""
    }
    Connections {
        target: card.controller
        function onImageAvailable(tmdbId, role, url) {
            if (tmdbId !== card.itemData.tmdb_id) return
            if (role === "poster") card.posterSource = url
            else if (role === "backdrop") card.backdropSource = url
        }
    }
    property bool busy: false
    signal opened(int tmdbId)
    signal watched(int tmdbId, int seasonNumber, int episodeNumber)
    implicitWidth: 510
    implicitHeight: 218
    color: Tokens.Theme.surface
    radius: Tokens.Theme.radiusLg
    border.color: Tokens.Theme.border
    clip: true

    Image {
        anchors.fill: parent
        source: card.backdropSource
        fillMode: Image.PreserveAspectCrop
        opacity: 0.2
        sourceSize.width: Math.round(card.width * Screen.devicePixelRatio)
        sourceSize.height: Math.round(card.height * Screen.devicePixelRatio)
    }
    RowLayout {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceMd
        spacing: Tokens.Theme.spaceMd

        Image {
            Layout.preferredWidth: 122
            Layout.fillHeight: true
            source: card.posterSource
            fillMode: Image.PreserveAspectCrop
            sourceSize.width: Math.round(122 * Screen.devicePixelRatio)
            sourceSize.height: Math.round(height * Screen.devicePixelRatio)
        }
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Tokens.Theme.spaceXs
            Label {
                Layout.fillWidth: true
                text: card.itemData.title || ""
                color: Tokens.Theme.textPrimary
                font.pixelSize: Tokens.Theme.textEmpty
                font.weight: Tokens.Theme.weightDemiBold
                elide: Text.ElideRight
            }
            Label {
                text: card.itemData.episodeCode || ""
                color: Tokens.Theme.accent
                font.pixelSize: Tokens.Theme.textBody
            }
            Label {
                Layout.fillWidth: true
                text: card.itemData.episode_title || "Bölüm adı yok"
                color: Tokens.Theme.textSecondary
                elide: Text.ElideRight
            }
            Label {
                text: (card.itemData.watched_count || 0) + " / "
                    + (card.itemData.aired_count || 0) + " bölüm izlendi"
                color: Tokens.Theme.textMuted
                font.pixelSize: Tokens.Theme.textSmall
            }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true
                IzlekButton {
                    objectName: "continueWatchedButton"
                    text: "İzlendi"
                    enabled: !card.busy
                    onClicked: card.watched(card.itemData.tmdb_id,
                                            card.itemData.season_number,
                                            card.itemData.episode_number)
                }
                IzlekButton {
                    text: "Detay"
                    variant: "secondary"
                    onClicked: card.opened(card.itemData.tmdb_id)
                }
            }
        }
    }
}
