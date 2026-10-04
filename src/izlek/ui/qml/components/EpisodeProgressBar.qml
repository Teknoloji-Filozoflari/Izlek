import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

ColumnLayout {
    id: progress
    property int watched: 0
    property int total: 0
    readonly property real fraction: total > 0 ? Math.max(0, Math.min(1, watched / total)) : 0
    spacing: Tokens.Theme.spaceXs
    RowLayout {
        Layout.fillWidth: true
        Label { text: "İlerleme"; color: Tokens.Theme.textMuted; font.pixelSize: Tokens.Theme.textSmall }
        Item { Layout.fillWidth: true }
        Label {
            text: progress.watched + " / " + (progress.total > 0 ? progress.total : "—") + " bölüm"
            color: Tokens.Theme.textSecondary
            font.pixelSize: Tokens.Theme.textSmall
        }
    }
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 7
        radius: height / 2
        color: Tokens.Theme.border
        Rectangle {
            width: parent.width * progress.fraction
            height: parent.height
            radius: parent.radius
            color: Tokens.Theme.statsAccent
            Behavior on width { NumberAnimation { duration: Tokens.Theme.animationNormal } }
        }
    }
}
