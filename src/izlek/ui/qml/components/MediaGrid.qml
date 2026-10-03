import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

GridView {
    id: grid
    property var items: []
    readonly property int columns: Math.max(1, Math.floor(width / (Tokens.Theme.cardWidth
                                                          + Tokens.Theme.gridGap)))
    signal mediaActivated(var media)
    model: items
    cellWidth: width / columns
    cellHeight: Tokens.Theme.cardHeight + Tokens.Theme.gridGap
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true

    delegate: MediaCardDelegate {
        required property var modelData
        media: modelData
        width: Math.min(Tokens.Theme.cardWidth, grid.cellWidth - Tokens.Theme.gridGap)
        height: Tokens.Theme.cardHeight
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
