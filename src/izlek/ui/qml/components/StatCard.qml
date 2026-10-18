import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Rectangle {
    id: card
    property string label: ""
    property string value: "—"
    property string detail: ""
    property bool accented: false
    implicitWidth: 190
    implicitHeight: 116
    radius: Tokens.Theme.radiusMd
    color: Tokens.Theme.surface
    border.color: accented ? Tokens.Theme.accent : Tokens.Theme.border
    Accessible.name: label + ": " + value + (detail.length ? ", " + detail : "")

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceMd
        spacing: Tokens.Theme.spaceXs
        Label {
            Layout.fillWidth: true
            text: card.label
            color: Tokens.Theme.textSecondary
            font.pixelSize: Tokens.Theme.textBody
            elide: Text.ElideRight
        }
        Label {
            objectName: "statValue"
            Layout.fillWidth: true
            text: card.value
            color: card.accented ? Tokens.Theme.accent : Tokens.Theme.textPrimary
            font.pixelSize: Tokens.Theme.textStat
            font.weight: Tokens.Theme.weightDemiBold
            elide: Text.ElideRight
        }
        Label {
            Layout.fillWidth: true
            visible: card.detail.length > 0
            text: card.detail
            color: Tokens.Theme.textMuted
            font.pixelSize: Tokens.Theme.textSmall
            elide: Text.ElideRight
        }
    }
}
