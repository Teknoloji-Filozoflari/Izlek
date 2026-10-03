import QtQuick
import "../theme" as Tokens

Rectangle {
    radius: Tokens.Theme.radiusSm
    color: Tokens.Theme.skeleton
    opacity: 0.55

    SequentialAnimation on opacity {
        running: parent.visible
        loops: Animation.Infinite
        NumberAnimation { from: 0.55; to: 1; duration: 700 }
        NumberAnimation { from: 1; to: 0.55; duration: 700 }
    }
}
