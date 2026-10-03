import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Item {
    id: header
    property string title: ""
    property string subtitle: ""
    property string actionText: ""
    signal actionTriggered()
    implicitHeight: row.implicitHeight
    implicitWidth: row.implicitWidth

    RowLayout {
        id: row
        anchors.fill: parent
        spacing: Tokens.Theme.spaceMd

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Tokens.Theme.spaceXs
            Label {
                text: header.title
                color: Tokens.Theme.textPrimary
                font.pixelSize: Tokens.Theme.textHeading
                font.weight: Tokens.Theme.weightDemiBold
            }
            Label {
                visible: header.subtitle.length > 0
                text: header.subtitle
                color: Tokens.Theme.textSecondary
                font.pixelSize: Tokens.Theme.textBody
            }
        }

        IzlekButton {
            visible: header.actionText.length > 0
            text: header.actionText
            variant: "ghost"
            onClicked: header.actionTriggered()
        }
    }
}
