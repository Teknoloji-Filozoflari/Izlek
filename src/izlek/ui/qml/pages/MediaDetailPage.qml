import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property var controller
    property string pageTitle: (i18n.revision, i18n.t("page.media_detail"))
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
        SplitView {
            visible: !!page.controller.detail.title
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            handle: PaneSplitHandle {}
            Image {
                SplitView.preferredWidth: 220
                SplitView.minimumWidth: 160
                SplitView.maximumWidth: 320
                SplitView.fillHeight: true
                source: page.controller.detail.poster || ""
                asynchronous: true
                fillMode: Image.PreserveAspectFit
            }
            ColumnLayout {
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumWidth: Tokens.Theme.contentMin
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
