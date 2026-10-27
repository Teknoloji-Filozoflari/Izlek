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
    readonly property real progressFraction: {
        var total = Number(itemData.aired_count) || 0
        if (total <= 0)
            return 0
        return Math.max(0, Math.min(1, (Number(itemData.watched_count) || 0) / total))
    }
    readonly property string episodeBadge: {
        var season = Number(itemData.season_number) || 0
        var episode = Number(itemData.episode_number) || 0
        if (season <= 0 || episode <= 0)
            return itemData.episodeCode || ""
        return "S" + season + "B" + episode
    }
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
    implicitWidth: 280
    implicitHeight: 158
    color: Tokens.Theme.surfaceElevated
    radius: Tokens.Theme.radiusMd
    border.color: Tokens.Theme.border
    clip: true
    activeFocusOnTab: true
    Accessible.name: (itemData.title || "") + " " + episodeBadge
    Accessible.role: Accessible.Button
    Accessible.onPressAction: card.opened(card.itemData.tmdb_id)
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter
                || event.key === Qt.Key_Space) {
            card.opened(card.itemData.tmdb_id)
            event.accepted = true
        }
    }

    Image {
        anchors.fill: parent
        source: card.backdropSource.toString() ? card.backdropSource : card.posterSource
        fillMode: Image.PreserveAspectCrop
        sourceSize.width: Math.round(card.width * Screen.devicePixelRatio)
        sourceSize.height: Math.round(card.height * Screen.devicePixelRatio)
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop {
                position: 0.0
                color: Qt.rgba(Tokens.Theme.background.r, Tokens.Theme.background.g,
                               Tokens.Theme.background.b, 0.0)
            }
            GradientStop {
                position: 0.45
                color: Qt.rgba(Tokens.Theme.background.r, Tokens.Theme.background.g,
                               Tokens.Theme.background.b, 0.4)
            }
            GradientStop {
                position: 1.0
                color: Qt.rgba(Tokens.Theme.background.r, Tokens.Theme.background.g,
                               Tokens.Theme.background.b, 0.9)
            }
        }
    }
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: card.opened(card.itemData.tmdb_id)
    }
    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: Tokens.Theme.spaceSm
        width: badgeLabel.implicitWidth + Tokens.Theme.spaceSm
        height: Tokens.Theme.controlHeight * 0.55
        radius: Tokens.Theme.radiusSm
        color: Qt.rgba(Tokens.Theme.background.r, Tokens.Theme.background.g,
                       Tokens.Theme.background.b, 0.8)
        border.color: Tokens.Theme.border
        Label {
            id: badgeLabel
            anchors.centerIn: parent
            text: card.episodeBadge
            color: Tokens.Theme.textPrimary
            font.pixelSize: Tokens.Theme.textSmall
            font.weight: Tokens.Theme.weightDemiBold
        }
    }
    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: progressTrack.top
        anchors.margins: Tokens.Theme.spaceSm
        spacing: Tokens.Theme.spaceXs
        Label {
            Layout.fillWidth: true
            text: card.itemData.title || ""
            color: Tokens.Theme.textPrimary
            font.pixelSize: Tokens.Theme.textBody
            font.weight: Tokens.Theme.weightDemiBold
            elide: Text.ElideRight
            maximumLineCount: 1
        }
        RowLayout {
            Layout.fillWidth: true
            Label {
                Layout.fillWidth: true
                text: card.itemData.episode_title || card.episodeBadge
                color: Tokens.Theme.textSecondary
                font.pixelSize: Tokens.Theme.textSmall
                elide: Text.ElideRight
            }
            IzlekButton {
                objectName: "continueWatchedButton"
                text: (i18n.revision, i18n.t("episode.watched"))
                variant: "secondary"
                enabled: !card.busy
                implicitHeight: Tokens.Theme.controlHeight * 0.7
                onClicked: card.watched(card.itemData.tmdb_id,
                                        card.itemData.season_number,
                                        card.itemData.episode_number)
            }
        }
    }
    Rectangle {
        id: progressTrack
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 4
        color: Tokens.Theme.border
        Rectangle {
            width: parent.width * card.progressFraction
            height: parent.height
            color: Tokens.Theme.danger
        }
    }
    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: "transparent"
        border.color: card.activeFocus ? Tokens.Theme.accent : "transparent"
        border.width: 2
    }
}
