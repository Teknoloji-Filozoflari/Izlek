import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    objectName: "settingsPage"
    property string pageTitle: "Ayarlar"
    property var controller
    property var transferModelController
    property bool editingToken: false
    color: Tokens.Theme.background

    component Card: Rectangle {
        property string title
        default property alias content: body.data
        Layout.fillWidth: true
        color: Tokens.Theme.surface
        radius: Tokens.Theme.radiusLg
        border.color: Tokens.Theme.border
        implicitHeight: body.implicitHeight + 2 * Tokens.Theme.spaceLg
        ColumnLayout {
            id: body
            anchors.fill: parent
            anchors.margins: Tokens.Theme.spaceLg
            spacing: Tokens.Theme.spaceMd
            Label { text: parent.parent.title; color: Tokens.Theme.textPrimary; font.pixelSize: Tokens.Theme.textEmpty; font.weight: Tokens.Theme.weightDemiBold }
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceXl
        contentWidth: width
        contentHeight: column.implicitHeight
        clip: true
        ColumnLayout {
            id: column
            width: parent.width
            spacing: Tokens.Theme.spaceLg
            Label { text: page.pageTitle; color: Tokens.Theme.textPrimary; font.pixelSize: Tokens.Theme.textHeading; font.weight: Tokens.Theme.weightDemiBold }

            Card { objectName: "tmdbSettingsCard"; title: "TMDb"
                Label { text: page.controller.hasToken ? "Bağlı — " + (page.controller.storageKind === "keyring" ? "sistem anahtarlığı" : "yerel dosya") : "Bağlı değil"; color: page.controller.hasToken ? Tokens.Theme.success : Tokens.Theme.warning }
                IzlekButton { objectName: "changeTokenButton"; text: page.editingToken ? "Vazgeç" : "Tokenı Değiştir"; variant: "secondary"; onClicked: { if (page.editingToken) tokenForm.clearInput(); page.editingToken = !page.editingToken } }
                TokenForm { id: tokenForm; visible: page.editingToken; controller: page.controller; heading: "Yeni token"; description: "Tokenı test edip kaydedin."; Layout.fillWidth: true }
            }

            Card { objectName: "dataSettingsCard"; title: "Veriler"
                Label { Layout.fillWidth: true; text: "Metadata, takip, favoriler, bölüm ilerlemesi ve listeleri İzlek JSON olarak yönetin. Token ve cache yolları dışarıda tutulur."; color: Tokens.Theme.textSecondary; wrapMode: Text.WordWrap }
                RowLayout { IzlekButton { objectName: "exportDataButton"; text: "Dışa Aktar"; enabled: !page.transferModelController.busy; onClicked: exportDialog.open() } IzlekButton { objectName: "selectImportButton"; text: "İçe Aktar"; variant: "secondary"; enabled: !page.transferModelController.busy; onClicked: importDialog.open() } }
                Label { visible: page.transferModelController.busy; text: "İşlem sürüyor…"; color: Tokens.Theme.textMuted }
                Label { objectName: "transferFeedback"; visible: page.transferModelController.feedback.length > 0; text: page.transferModelController.feedback; color: page.transferModelController.feedbackKind === "danger" ? Tokens.Theme.danger : Tokens.Theme.success; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Rectangle { objectName: "importPreview"; visible: Object.keys(page.transferModelController.preview).length > 0; Layout.fillWidth: true; implicitHeight: preview.implicitHeight + 2 * Tokens.Theme.spaceMd; color: Tokens.Theme.surfaceElevated; radius: Tokens.Theme.radiusMd; border.color: Tokens.Theme.border
                    ColumnLayout { id: preview; anchors.fill: parent; anchors.margins: Tokens.Theme.spaceMd; Label { text: "Import özeti"; color: Tokens.Theme.textPrimary } Label { text: (page.transferModelController.preview.movies || 0) + " film · " + (page.transferModelController.preview.shows || 0) + " dizi · " + (page.transferModelController.preview.episode_progress || 0) + " bölüm"; color: Tokens.Theme.textSecondary } IzlekButton { objectName: "confirmImportButton"; text: "İçe Aktar"; onClicked: page.transferModelController.importSelected() } }
                }
            }

            Card { objectName: "cacheSettingsCard"; title: "Cache"
                Label { text: "Mevcut cache boyutu: " + cacheController.sizeLabel; color: Tokens.Theme.textSecondary }
                RowLayout { IzlekButton { objectName: "refreshCacheButton"; text: "Yenile"; variant: "secondary"; enabled: !cacheController.busy; onClicked: cacheController.refresh() } IzlekButton { objectName: "clearCacheButton"; text: "Cache Temizle"; enabled: !cacheController.busy; onClicked: cacheController.clear() } }
                Label { visible: cacheController.feedback.length > 0; text: cacheController.feedback; color: cacheController.feedbackKind === "danger" ? Tokens.Theme.danger : Tokens.Theme.success; wrapMode: Text.WordWrap }
            }

            Card { objectName: "shortcutsSettingsCard"; title: "Kısayollar"
                Repeater { model: ["Ctrl+K  Arama", "Ctrl+1  Ana Sayfa", "Ctrl+2  Filmler", "Ctrl+3  Diziler", "Ctrl+4  Listeler", "Ctrl+5  Keşfet", "Ctrl+,  Ayarlar", "Esc  Kapat / Geri"]; delegate: Label { text: modelData; color: Tokens.Theme.textSecondary } }
            }
            Card { objectName: "aboutSettingsCard"; title: "Hakkında"
                Label { text: "İzlek  ·  sürüm " + appVersion; color: Tokens.Theme.textSecondary }
                Label { text: "GPL-3.0-or-later"; color: Tokens.Theme.textSecondary }
                Label { objectName: "tmdbDataSourceLabel"; Layout.fillWidth: true; text: "Film, dizi, kişi, puan ve görsel bilgileri TMDB tarafından sağlanır; takip durumları, favoriler ve listeler yalnızca İzlek'in yerel verisidir."; color: Tokens.Theme.textMuted; wrapMode: Text.WordWrap }
                Label { objectName: "tmdbAttributionNotice"; Layout.fillWidth: true; text: "This product uses the TMDB API but is not endorsed or certified by TMDB."; color: Tokens.Theme.textSecondary; wrapMode: Text.WordWrap }
                Label { objectName: "justWatchAttributionLabel"; Layout.fillWidth: true; text: "İzleme sağlayıcısı uygunluğu verisi JustWatch tarafından sağlanır."; color: Tokens.Theme.textMuted; wrapMode: Text.WordWrap }
                IzlekButton { objectName: "tmdbWebsiteButton"; text: "TMDB"; variant: "secondary"; onClicked: Qt.openUrlExternally("https://www.themoviedb.org") }
                IzlekButton { objectName: "githubButton"; text: "GitHub"; variant: "secondary"; onClicked: Qt.openUrlExternally("https://github.com") }
            }
            Item { Layout.preferredHeight: Tokens.Theme.spaceLg }
        }
    }
    FileDialog { id: exportDialog; objectName: "exportFileDialog"; title: "İzlek verisini dışa aktar"; fileMode: FileDialog.SaveFile; nameFilters: ["İzlek JSON (*.json)"]; defaultSuffix: "json"; onAccepted: page.transferModelController.exportTo(selectedFile.toString()) }
    FileDialog { id: importDialog; objectName: "importFileDialog"; title: "İzlek JSON dosyası seç"; fileMode: FileDialog.OpenFile; nameFilters: ["İzlek JSON (*.json)", "JSON (*.json)"]; onAccepted: page.transferModelController.previewImport(selectedFile.toString()) }
}
