import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

GridView {
    id: grid
    property var items: []
    property var quickLibraryController: null
    property var dismissController: null
    property bool compact: false
    readonly property int targetCardWidth: compact ? Tokens.Theme.cardCompactWidth : Tokens.Theme.cardWidth
    readonly property real posterCardWidth: Math.min(targetCardWidth, cellWidth - Tokens.Theme.gridGap)
    readonly property real posterCardHeight: Math.round(posterCardWidth * 1.5) + Tokens.Theme.cardInfoHeight
        + (quickLibraryController ? Tokens.Theme.controlHeight + Tokens.Theme.spaceSm : 0)
    readonly property int columns: Math.max(1, Math.floor(width / (targetCardWidth
                                                          + Tokens.Theme.gridGap)))
    signal mediaActivated(var media)
    model: items
    cellWidth: width / columns
    cellHeight: posterCardHeight + Tokens.Theme.gridGap
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true

    delegate: MediaCardDelegate {
        required property var modelData
        media: modelData
        quickLibraryController: grid.quickLibraryController
        dismissController: grid.dismissController
        width: grid.posterCardWidth
        height: grid.posterCardHeight
        onActivated: grid.mediaActivated(media)
    }

    ScrollBar.vertical: ScrollBar {
        policy: grid.contentHeight > grid.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
        contentItem: Rectangle {
            implicitWidth: 5
            radius: 2
            color: Tokens.Theme.border
        }
    }
}
