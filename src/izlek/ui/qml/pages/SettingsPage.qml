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
    property var metadataModelController
    property bool editingToken: false
    property int regionComboIndex: 0
    color: Tokens.Theme.background
    Component.onCompleted: {
        personalController.refreshHidden()
        syncRegionCombo()
    }

    function syncRegionCombo() {
        if (!page.metadataModelController)
            return
        const code = page.metadataModelController.watchProviderRegion
        const regions = page.metadataModelController.watchProviderRegions
        for (let i = 0; i < regions.length; i++) {
            if (regions[i].code === code) {
                page.regionComboIndex = i
                return
            }
        }
        page.regionComboIndex = 0
    }

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

            Card { objectName: "watchRegionSettingsCard"; title: "İzleme bölgesi"
                Label {
                    Layout.fillWidth: true
                    text: "Nerede İzlenir bölümü TMDb/JustWatch verisini seçilen ülke koduna göre gösterir. Varsayılan Türkiye (TR)."
                    color: Tokens.Theme.textSecondary
                    wrapMode: Text.WordWrap
                }
                FilterComboBox {
                    id: regionCombo
                    objectName: "watchProviderRegionCombo"
                    Layout.preferredWidth: 280
                    model: page.metadataModelController ? page.metadataModelController.watchProviderRegions : []
                    textRole: "label"
                    currentIndex: page.regionComboIndex
                    onActivated: (index) => {
                        page.regionComboIndex = index
                        const item = model[index]
                        if (item && page.metadataModelController)
                            page.metadataModelController.setWatchProviderRegion(item.code)
                    }
                }
                Connections {
                    target: page.metadataModelController
                    function onChanged() { page.syncRegionCombo() }
                }
            }

            Card { objectName: "metadataSourcesSettingsCard"; title: "Meta veri kaynakları"
                Label {
                    Layout.fillWidth: true
                    text: "TMDb varsayılan katalog kaynağıdır. Trakt, TVmaze ve OMDb isteğe bağlıdır; her kaynakta yalnızca uygulamanın ihtiyaç duyduğu yetenekler açılabilir. Kimlikler anahtarlıkta tutulur."
                    color: Tokens.Theme.textSecondary
                    wrapMode: Text.WordWrap
                }
                Label {
                    objectName: "metadataSourcesFeedback"
                    visible: page.metadataModelController && page.metadataModelController.feedback.length > 0
                    text: page.metadataModelController ? page.metadataModelController.feedback : ""
                    color: page.metadataModelController && page.metadataModelController.feedbackKind === "danger"
                           ? Tokens.Theme.danger
                           : (page.metadataModelController && page.metadataModelController.feedbackKind === "warning"
                              ? Tokens.Theme.warning : Tokens.Theme.success)
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Repeater {
                    model: page.metadataModelController ? page.metadataModelController.sources : []
                    delegate: Rectangle {
                        id: sourceCard
                        required property var modelData
                        readonly property string sourceId: modelData.id
                        Layout.fillWidth: true
                        implicitHeight: sourceColumn.implicitHeight + 2 * Tokens.Theme.spaceMd
                        color: Tokens.Theme.surfaceElevated
                        radius: Tokens.Theme.radiusMd
                        border.color: Tokens.Theme.border
                        ColumnLayout {
                            id: sourceColumn
                            anchors.fill: parent
                            anchors.margins: Tokens.Theme.spaceMd
                            spacing: Tokens.Theme.spaceSm
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: sourceCard.modelData.label + (sourceCard.modelData.isDefault ? " (varsayılan)" : "")
                                    color: Tokens.Theme.textPrimary
                                    font.weight: Tokens.Theme.weightDemiBold
                                    Layout.fillWidth: true
                                }
                                Switch {
                                    objectName: "metadataSourceEnabledSwitch"
                                    checked: sourceCard.modelData.enabled
                                    enabled: !sourceCard.modelData.isDefault
                                    onToggled: page.metadataModelController.setSourceEnabled(sourceCard.sourceId, checked)
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: sourceCard.modelData.summary
                                color: Tokens.Theme.textSecondary
                                wrapMode: Text.WordWrap
                            }
                            Label {
                                Layout.fillWidth: true
                                text: sourceCard.modelData.notes
                                color: Tokens.Theme.textMuted
                                wrapMode: Text.WordWrap
                                font.pixelSize: Tokens.Theme.textSmall
                            }
                            Flow {
                                Layout.fillWidth: true
                                spacing: Tokens.Theme.spaceSm
                                Repeater {
                                    model: sourceCard.modelData.capabilities
                                    delegate: CheckBox {
                                        required property var modelData
                                        objectName: "metadataCapabilityCheck"
                                        text: modelData.label
                                        checked: modelData.enabled
                                        ToolTip.visible: hovered
                                        ToolTip.text: modelData.description
                                        onToggled: page.metadataModelController.setSourceCapability(
                                                       sourceCard.sourceId, modelData.id, checked)
                                    }
                                }
                            }
                            RowLayout {
                                visible: sourceCard.modelData.requiresNonCommercialAck
                                Layout.fillWidth: true
                                CheckBox {
                                    objectName: "omdbNonCommercialCheck"
                                    text: "Kişisel / ticari olmayan kullanım — OMDb şartlarını kabul ediyorum"
                                    checked: sourceCard.modelData.omdbNonCommercialAcknowledged
                                    onToggled: page.metadataModelController.acknowledgeOmdbNonCommercial(checked)
                                }
                            }
                            RowLayout {
                                visible: sourceCard.modelData.credentialKind !== "none" && sourceCard.sourceId !== "tmdb"
                                Layout.fillWidth: true
                                TextField {
                                    id: credentialField
                                    objectName: "metadataCredentialInput"
                                    Layout.fillWidth: true
                                    echoMode: TextInput.Password
                                    placeholderText: sourceCard.modelData.credentialLabel || "API kimliği"
                                    color: Tokens.Theme.textPrimary
                                    placeholderTextColor: Tokens.Theme.textMuted
                                    background: Rectangle {
                                        color: Tokens.Theme.surface
                                        radius: Tokens.Theme.radiusSm
                                        border.color: credentialField.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
                                        border.width: credentialField.activeFocus ? 2 : 1
                                    }
                                }
                                IzlekButton {
                                    objectName: "saveMetadataCredentialButton"
                                    text: sourceCard.modelData.hasCredential ? "Güncelle" : "Kaydet"
                                    variant: "secondary"
                                    onClicked: page.metadataModelController.saveSourceCredential(
                                                   sourceCard.sourceId, credentialField.text)
                                }
                                IzlekButton {
                                    objectName: "clearMetadataCredentialButton"
                                    text: "Sil"
                                    variant: "ghost"
                                    visible: sourceCard.modelData.hasCredential
                                    onClicked: page.metadataModelController.clearSourceCredential(sourceCard.sourceId)
                                }
                            }
                        }
                    }
                }
            }

            Card { objectName: "dataSettingsCard"; title: "Veriler"
                Label { Layout.fillWidth: true; text: "İzlek JSON dışa/içe aktarır; Trakt JSON ve Letterboxd CSV (tmdbID sütunlu) içe aktarılabilir. Token ve cache yolları dışarıda tutulur."; color: Tokens.Theme.textSecondary; wrapMode: Text.WordWrap }
                RowLayout { IzlekButton { objectName: "exportDataButton"; text: "Dışa Aktar"; enabled: !page.transferModelController.busy; onClicked: exportDialog.open() } IzlekButton { objectName: "selectImportButton"; text: "İçe Aktar"; variant: "secondary"; enabled: !page.transferModelController.busy; onClicked: importDialog.open() } }
                Label { visible: page.transferModelController.busy; text: "İşlem sürüyor…"; color: Tokens.Theme.textMuted }
                Label { objectName: "transferFeedback"; visible: page.transferModelController.feedback.length > 0; text: page.transferModelController.feedback; color: page.transferModelController.feedbackKind === "danger" ? Tokens.Theme.danger : Tokens.Theme.success; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Rectangle { objectName: "importPreview"; visible: Object.keys(page.transferModelController.preview).length > 0; Layout.fillWidth: true; implicitHeight: preview.implicitHeight + 2 * Tokens.Theme.spaceMd; color: Tokens.Theme.surfaceElevated; radius: Tokens.Theme.radiusMd; border.color: Tokens.Theme.border
                    ColumnLayout { id: preview; anchors.fill: parent; anchors.margins: Tokens.Theme.spaceMd; Label { text: "Import özeti" + (page.transferModelController.preview.source ? (" · " + page.transferModelController.preview.source) : ""); color: Tokens.Theme.textPrimary } Label { text: (page.transferModelController.preview.movies || 0) + " film · " + (page.transferModelController.preview.shows || 0) + " dizi · " + (page.transferModelController.preview.episode_progress || 0) + " bölüm"; color: Tokens.Theme.textSecondary } IzlekButton { objectName: "confirmImportButton"; text: "İçe Aktar"; onClicked: page.transferModelController.importSelected() } }
                }
            }

            Card { objectName: "cacheSettingsCard"; title: "Cache"
                Label { Layout.fillWidth: true; text: "Kütüphanedeki film ve dizilerin indirilen görselleri yerelde tutulur ve cache temizliğinde korunur. Diğer görseller ve film/dizi bilgileri 180 gün sonunda temizlenir. İzleme durumları, bölüm ilerlemeleri, favoriler ve listeler korunur."; color: Tokens.Theme.textMuted; wrapMode: Text.WordWrap }
                Label { text: "Mevcut cache boyutu: " + cacheController.sizeLabel; color: Tokens.Theme.textSecondary }
                RowLayout { IzlekButton { objectName: "refreshCacheButton"; text: "Yenile"; variant: "secondary"; enabled: !cacheController.busy; onClicked: cacheController.refresh() } IzlekButton { objectName: "clearCacheButton"; text: "Cache Temizle"; enabled: !cacheController.busy; onClicked: cacheController.clear() } }
                Label { visible: cacheController.feedback.length > 0; text: cacheController.feedback; color: cacheController.feedbackKind === "danger" ? Tokens.Theme.danger : Tokens.Theme.success; wrapMode: Text.WordWrap }
            }

            Card { objectName: "hiddenMediaSettingsCard"; title: "Önerilerden gizlediklerim"
                Label { Layout.fillWidth: true; text: "Gizlenen içerikler Keşfet ve içerik önerilerinde gösterilmez. İstediğini yeniden açabilirsin."; color: Tokens.Theme.textSecondary; wrapMode: Text.WordWrap }
                Label { visible: personalController.hiddenItems.length === 0; text: "Gizlenen içerik yok."; color: Tokens.Theme.textMuted }
                ListView {
                    objectName: "hiddenMediaList"
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(280, count * 56)
                    model: personalController.hiddenItems
                    clip: true
                    delegate: RowLayout {
                        required property var modelData
                        width: ListView.view.width
                        height: 56
                        Label { Layout.fillWidth: true; text: modelData.title + (modelData.mediaType === "movie" ? " · Film" : " · Dizi"); elide: Text.ElideRight; color: Tokens.Theme.textPrimary }
                        IzlekButton { objectName: "restoreHiddenMediaButton"; text: "Yeniden göster"; variant: "secondary"; enabled: !personalController.busy; onClicked: personalController.setDismissed(modelData, false) }
                    }
                    ScrollBar.vertical: ScrollBar {}
                }
                Label { visible: !!personalController.feedback; text: personalController.feedback; color: Tokens.Theme.textSecondary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            }
            Card { objectName: "shortcutsSettingsCard"; title: "Kısayollar"
                Repeater { model: ["Ctrl+K  Arama", "Ctrl+1  Ana Sayfa / Keşfet", "Ctrl+2  Filmler", "Ctrl+3  Diziler", "Ctrl+4  Listeler", "Ctrl+5  İstatistikler", "Ctrl+,  Ayarlar", "Esc  Kapat / Geri"]; delegate: Label { text: modelData; color: Tokens.Theme.textSecondary } }
            }
            Card { objectName: "aboutSettingsCard"; title: "Hakkında"
                Image { objectName: "tmdbLogo"; source: "../../../resources/images/tmdb.svg"; Layout.preferredWidth: 116; Layout.preferredHeight: 16; fillMode: Image.PreserveAspectFit; Accessible.name: "The Movie Database (TMDB)" }
                Label { text: "İzlek  ·  sürüm " + appVersion; color: Tokens.Theme.textSecondary }
                Label { text: "GPL-3.0-or-later"; color: Tokens.Theme.textSecondary }
                Label { objectName: "tmdbDataSourceLabel"; Layout.fillWidth: true; text: "Film, dizi, kişi, puan ve görsel bilgileri TMDB tarafından sağlanır; takip durumları, favoriler ve listeler yalnızca İzlek'in yerel verisidir."; color: Tokens.Theme.textMuted; wrapMode: Text.WordWrap }
                Label { objectName: "tmdbAttributionNotice"; Layout.fillWidth: true; text: "This product uses the TMDB API but is not endorsed or certified by TMDB."; color: Tokens.Theme.textSecondary; wrapMode: Text.WordWrap }
                Label { objectName: "justWatchAttributionLabel"; Layout.fillWidth: true; text: "İzleme sağlayıcısı uygunluğu verisi JustWatch tarafından sağlanır."; color: Tokens.Theme.textMuted; wrapMode: Text.WordWrap }
                IzlekButton { objectName: "tmdbWebsiteButton"; text: "TMDB"; variant: "secondary"; onClicked: Qt.openUrlExternally("https://www.themoviedb.org") }
                IzlekButton { objectName: "githubButton"; text: "GitHub"; variant: "secondary"; onClicked: Qt.openUrlExternally("https://github.com/Teknoloji-Filozoflari/Izlek") }
            }
            Item { Layout.preferredHeight: Tokens.Theme.spaceLg }
        }
    }
    FileDialog { id: exportDialog; objectName: "exportFileDialog"; title: "İzlek verisini dışa aktar"; fileMode: FileDialog.SaveFile; nameFilters: ["İzlek JSON (*.json)"]; defaultSuffix: "json"; onAccepted: page.transferModelController.exportTo(selectedFile.toString()) }
    FileDialog { id: importDialog; objectName: "importFileDialog"; title: "İçe aktarma dosyası seç"; fileMode: FileDialog.OpenFile; nameFilters: ["Desteklenen (*.json *.csv)", "İzlek / Trakt JSON (*.json)", "Letterboxd CSV (*.csv)"]; onAccepted: page.transferModelController.previewImport(selectedFile.toString()) }
}
