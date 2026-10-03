import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Rectangle {
    id: card
    property string label: ""
    property string value: "—"
    property string detail: ""
    implicitWidth: 190
    implicitHeight: 116
    radius: Tokens.Theme.radiusMd
    color: Tokens.Theme.surface
    border.color: Tokens.Theme.border

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceMd
        spacing: Tokens.Theme.spaceXs
        Label {
            text: card.label
            color: Tokens.Theme.textSecondary
            font.pixelSize: Tokens.Theme.textBody
        }
        Label {
            text: card.value
            color: Tokens.Theme.textPrimary
            font.pixelSize: Tokens.Theme.textStat
            font.weight: Tokens.Theme.weightDemiBold
        }
        Label {
            visible: card.detail.length > 0
            text: card.detail
            color: Tokens.Theme.textMuted
            font.pixelSize: Tokens.Theme.textSmall
        }
    }
}
