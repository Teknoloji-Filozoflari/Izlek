import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property var controller
    color: Tokens.Theme.background

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(520, parent.width - 2 * Tokens.Theme.spaceLg)
        implicitHeight: content.implicitHeight + 2 * Tokens.Theme.space2xl
        height: implicitHeight
        color: Tokens.Theme.surface
        radius: Tokens.Theme.radiusLg
        border.color: Tokens.Theme.border

        ColumnLayout {
            id: content
            anchors.fill: parent
            anchors.margins: Tokens.Theme.space2xl
            spacing: Tokens.Theme.spaceLg

            RowLayout {
                spacing: Tokens.Theme.spaceMd
                Image {
                    source: Qt.resolvedUrl("../../../resources/icons/izlek.svg")
                    sourceSize.width: 56
                    sourceSize.height: 56
                    Layout.preferredWidth: 56
                    Layout.preferredHeight: 56
                }
                Label {
                    text: "İzlek"
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textStat
                    font.weight: Tokens.Theme.weightDemiBold
                }
            }
            Label {
                text: "Film ve dizilerini yerel olarak takip etmeye başla. "
                      + "İçerik bilgileri için TMDb Read Access Token gerekiyor."
                color: Tokens.Theme.textSecondary
                font.pixelSize: Tokens.Theme.textBody
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            TokenForm {
                controller: page.controller
                heading: "Başlamak için bağlan"
                Layout.fillWidth: true
            }
        }
    }
}
