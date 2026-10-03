import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Rectangle {
    id: page
    property string pageTitle: ""
    property string pageDescription: ""
    color: Tokens.Theme.background

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceXl
        spacing: Tokens.Theme.spaceLg

        ColumnLayout {
            spacing: Tokens.Theme.spaceXs
            Label {
                text: page.pageTitle
                color: Tokens.Theme.textPrimary
                font.pixelSize: Tokens.Theme.textHeading
                font.weight: Tokens.Theme.weightDemiBold
            }
            Label {
                text: page.pageDescription
                color: Tokens.Theme.textSecondary
                font.pixelSize: Tokens.Theme.textBody
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Tokens.Theme.surface
            radius: Tokens.Theme.radiusLg
            border.color: Tokens.Theme.border

            ColumnLayout {
                anchors.centerIn: parent
                spacing: Tokens.Theme.spaceMd

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    width: 46
                    height: 4
                    radius: 2
                    color: Tokens.Theme.accent
                }

                Label {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Henüz içerik yok"
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textEmpty
                    font.weight: Tokens.Theme.weightMedium
                }
            }
        }
    }
}
