import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

ListView {
    id: strip
    property var items: []
    signal mediaActivated(var media)
    orientation: ListView.Horizontal
    model: items
    spacing: Tokens.Theme.gridGap
    implicitHeight: Tokens.Theme.cardHeight
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true

    delegate: MediaCardDelegate {
        required property var modelData
        media: modelData
        width: Tokens.Theme.cardWidth
        height: Tokens.Theme.cardHeight
        onActivated: strip.mediaActivated(media)
    }

    ScrollBar.horizontal: ScrollBar {
        policy: strip.contentWidth > strip.width ? ScrollBar.AsNeeded
                                                 : ScrollBar.AlwaysOff
        contentItem: Rectangle {
            implicitHeight: 5
            radius: 2
            color: Tokens.Theme.border
        }
    }
}
