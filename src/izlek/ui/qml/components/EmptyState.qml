import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Item {
    id: state
    property string title: "Henüz içerik yok"
    property string description: ""
    property string actionText: ""
    signal actionRequested()
    implicitHeight: 206
    implicitWidth: 280

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width, 380)
        spacing: Tokens.Theme.spaceSm

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: "◎"
            color: Tokens.Theme.accent
            font.pixelSize: Tokens.Theme.textStat
        }
        Label {
            Layout.fillWidth: true
            text: state.title
            color: Tokens.Theme.textPrimary
            font.pixelSize: Tokens.Theme.textEmpty
            font.weight: Tokens.Theme.weightDemiBold
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
        Label {
            visible: state.description.length > 0
            Layout.fillWidth: true
            text: state.description
            color: Tokens.Theme.textSecondary
            font.pixelSize: Tokens.Theme.textBody
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
        IzlekButton {
            visible: state.actionText.length > 0
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: Tokens.Theme.spaceSm
            text: state.actionText
            onClicked: state.actionRequested()
        }
    }
}
