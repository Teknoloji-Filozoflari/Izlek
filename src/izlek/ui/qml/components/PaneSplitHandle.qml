import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

Item {
    implicitWidth: 10
    implicitHeight: 10

    Rectangle {
        anchors.centerIn: parent
        width: parent.width >= parent.height ? 2 : Math.max(24, parent.width * 0.35)
        height: parent.width >= parent.height ? Math.max(24, parent.height * 0.35) : 2
        radius: 1
        color: SplitHandle.hovered || SplitHandle.pressed
               ? Tokens.Theme.accent : Tokens.Theme.border
    }
}
