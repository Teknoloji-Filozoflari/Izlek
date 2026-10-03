import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property var controller
    property string pageTitle: "Medya Detayı"
    signal backRequested()
    color: Tokens.Theme.background

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceXl
        spacing: Tokens.Theme.spaceLg
        IzlekButton {
            text: "← Geri"
            variant: "secondary"
            onClicked: page.backRequested()
        }
        BusyIndicator {
            visible: page.controller.detailBusy
            running: visible
            Layout.alignment: Qt.AlignHCenter
        }
        EmptyState {
            visible: !!page.controller.detailError
            Layout.fillWidth: true
            title: "Detay yüklenemedi"
            description: page.controller.detailError
        }
        RowLayout {
            visible: !!page.controller.detail.title
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Tokens.Theme.spaceXl
            Image {
                Layout.preferredWidth: 220
                Layout.preferredHeight: 330
                Layout.alignment: Qt.AlignTop
                source: page.controller.detail.poster || ""
                asynchronous: true
                fillMode: Image.PreserveAspectFit
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: Tokens.Theme.spaceMd
                Label {
                    Layout.fillWidth: true
                    text: page.controller.detail.title || ""
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textHeading
                    font.weight: Tokens.Theme.weightDemiBold
                    wrapMode: Text.WordWrap
                }
                Label {
                    text: (page.controller.detail.year || "Yıl bilinmiyor") + " · "
                          + (page.controller.detail.mediaType === "movie" ? "Film" : "Dizi")
                    color: Tokens.Theme.textSecondary
                    font.pixelSize: Tokens.Theme.textBody
                }
                Label {
                    Layout.fillWidth: true
                    text: page.controller.detail.overview || "Açıklama bulunmuyor."
                    color: Tokens.Theme.textSecondary
                    font.pixelSize: Tokens.Theme.textBody
                    wrapMode: Text.WordWrap
                }
            }
        }
        Item { Layout.fillHeight: true }
    }
}
