import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

Button {
    id: card
    property url posterSource
    property bool posterLoading: false
    property string mediaTitle: ""
    property string year: ""
    property real score: -1
    property real footerHeight: 0
    property string status: ""
    property real progress: -1
    property string progressText: ""
    property bool favorite: false
    property bool favoriteEnabled: false
    property bool reorderEnabled: false
    property bool selectionEnabled: false
    property bool selected: false
    property int personalRating: 0
    property var reorderView: null
    readonly property bool reorderDragging: directDrag.dragging
    readonly property bool posterReady: poster.status === Image.Ready
    readonly property string statusLabel: status === "PLANNED" ? (i18n.revision, i18n.t("status.planned"))
                                          : status === "WATCHING" ? (i18n.revision, i18n.t("status.watching"))
                                          : status === "WATCHED" ? (i18n.revision, i18n.t("status.watched"))
                                          : status === "SAVED" ? (i18n.revision, i18n.t("status.saved")) : ""
    signal activated()
    signal favoriteToggled(bool favorite)
    signal reorderDropped(point scenePosition)
    signal selectionToggled()

    implicitWidth: Tokens.Theme.cardWidth
    implicitHeight: Math.round(width * 1.5) + Tokens.Theme.cardInfoHeight + footerHeight
    padding: 0
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: mediaTitle + (year.length ? ", " + year : "")
                     + (score >= 0 ? ", TMDb " + score.toFixed(1) : "")
                     + (statusLabel.length ? ", " + statusLabel : "")
                     + (progressText.length ? ", " + progressText : "")
    onClicked: activated()
    Keys.onReturnPressed: function(event) { card.activated(); event.accepted = true }
    Keys.onEnterPressed: function(event) { card.activated(); event.accepted = true }

    contentItem: Item {
        ReorderHandle {
            id: directDrag
            objectName: "cardDragArea"
            anchors.fill: parent
            visible: card.reorderEnabled
            enabled: visible
            showHandle: false
            label: card.mediaTitle
            previewSource: card.posterSource
            onPressStarted: card.forceActiveFocus(Qt.MouseFocusReason)
            onTapped: card.clicked()
            onDropped: function(position) { card.reorderDropped(position) }
            ReorderAutoScroll {
                view: card.reorderView
                active: directDrag.dragging
                scenePosition: directDrag.scenePosition
            }
        }
        Column {
            width: parent.width
            z: 1
            opacity: card.reorderDragging ? 0.55 : 1
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
                    visible: card.posterLoading || poster.status === Image.Loading
                }

                Column {
                    visible: !card.posterLoading && poster.status !== Image.Loading && !card.posterReady
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
                    objectName: "cardStatus"
                    visible: card.statusLabel.length > 0
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.margins: Tokens.Theme.spaceSm
                    text: card.statusLabel
                    tone: card.status === "WATCHING" ? "accent"
                          : card.status === "WATCHED" ? "success" : "neutral"
                }
                Badge {
                    objectName: "cardScore"
                    visible: card.score >= 0
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.margins: Tokens.Theme.spaceSm
                    text: "★ " + card.score.toFixed(1)
                    tone: "accent"
                    Accessible.name: "TMDb puanı " + card.score.toFixed(1)
                }
                Badge {
                    objectName: "cardPersonalRating"
                    visible: card.personalRating > 0
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.leftMargin: Tokens.Theme.spaceSm
                    anchors.topMargin: card.score >= 0 ? 38 : Tokens.Theme.spaceSm
                    text: "Ben: " + card.personalRating + "/10"
                    tone: "neutral"
                }
                CheckBox {
                    objectName: "libraryCardSelection"
                    visible: card.selectionEnabled
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.rightMargin: Tokens.Theme.spaceXs
                    anchors.topMargin: Tokens.Theme.controlHeight + Tokens.Theme.spaceSm
                    checked: card.selected
                    Accessible.name: card.mediaTitle + " seç"
                    onClicked: card.selectionToggled()
                    indicator: Rectangle {
                        width: 26; height: 26
                        x: 6; y: 6
                        radius: Tokens.Theme.radiusSm
                        color: card.selected ? Tokens.Theme.accent : Tokens.Theme.surface
                        border.color: Tokens.Theme.accent
                        Text { anchors.centerIn: parent; text: card.selected ? "✓" : ""; color: Tokens.Theme.textPrimary }
                    }
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
                    objectName: "cardTitle"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Tokens.Theme.spaceSm
                    text: card.mediaTitle
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textBody
                    font.weight: Tokens.Theme.weightDemiBold
                    height: Tokens.Theme.cardTitleHeight
                    maximumLineCount: 2
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                }
                Label {
                    id: metaLabel
                    objectName: "cardMeta"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: titleLabel.bottom
                    anchors.topMargin: Tokens.Theme.spaceXs
                    anchors.leftMargin: Tokens.Theme.spaceSm
                    anchors.rightMargin: Tokens.Theme.spaceSm
                    text: card.progressText.length
                        ? (card.year.length ? card.year + " · " : "") + card.progressText
                        : card.year
                    color: Tokens.Theme.textSecondary
                    font.pixelSize: Tokens.Theme.textSmall
                    height: 18
                    elide: Text.ElideRight
                }
                Rectangle {
                    objectName: "cardProgress"
                    visible: card.progress >= 0
                    anchors.left: parent.left
                    anchors.right: parent.right
                    y: Tokens.Theme.cardInfoHeight - height - Tokens.Theme.spaceXs
                    anchors.margins: Tokens.Theme.spaceSm
                    height: 5
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
    }
    ToolTip.visible: hovered && !reorderDragging && (titleLabel.truncated || reorderEnabled)
    ToolTip.delay: 700
    ToolTip.text: mediaTitle + (reorderEnabled ? "\nYerini değiştirmek için tutup sürükle" : "")

    background: Rectangle {
        color: card.hovered ? Tokens.Theme.surfaceElevated : Tokens.Theme.surface
        radius: Tokens.Theme.radiusMd
        border.width: card.activeFocus || card.selected || card.reorderDragging ? 2 : card.hovered ? 1 : 0
        border.color: card.activeFocus || card.selected || card.reorderDragging ? Tokens.Theme.accent : Tokens.Theme.border
    }
}
