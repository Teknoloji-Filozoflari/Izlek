import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    objectName: "settingsPage"
    readonly property int _i18n: i18n.revision
    property string pageTitle: (i18n.revision, i18n.t("page.settings"))
    property var controller
    property var transferModelController
    property bool editingToken: false
    color: Tokens.Theme.background
    Component.onCompleted: personalController.refreshHidden()

    function tr(key) { return i18n.revision, i18n.t(key) }

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

            Card {
                objectName: "languageSettingsCard"
                title: page.tr("settings.language")
                Label {
                    Layout.fillWidth: true
                    text: page.tr("settings.language_help")
                    color: Tokens.Theme.textSecondary
                    wrapMode: Text.WordWrap
                }
                ComboBox {
                    id: languagePicker
                    objectName: "languagePicker"
                    Layout.fillWidth: true
                    Layout.preferredWidth: 280
                    model: i18n.availableLocales
                    textRole: "nativeName"
                    valueRole: "code"
                    currentIndex: {
                        const codes = i18n.availableLocales.map(item => item.code)
                        const index = codes.indexOf(i18n.locale)
                        return index >= 0 ? index : 0
                    }
                    onActivated: i18n.setLocale(currentValue)
                    Accessible.name: page.tr("settings.language")
                }
            }

            Card { objectName: "tmdbSettingsCard"; title: page.tr("settings.tmdb")
                Label {
                    text: page.controller.hasToken
                          ? (page.controller.storageKind === "keyring"
                             ? page.tr("token.connected_keyring")
                             : page.tr("token.connected_file"))
                          : page.tr("token.disconnected")
                    color: page.controller.hasToken ? Tokens.Theme.success : Tokens.Theme.warning
                }
                IzlekButton {
                    objectName: "changeTokenButton"
                    text: page.editingToken ? page.tr("common.cancel") : page.tr("token.change")
                    variant: "secondary"
                    onClicked: {
                        if (page.editingToken) tokenForm.clearInput()
                        page.editingToken = !page.editingToken
                    }
                }
                TokenForm {
                    id: tokenForm
                    visible: page.editingToken
                    controller: page.controller
                    heading: page.tr("token.new_heading")
                    description: page.tr("token.new_description")
                    Layout.fillWidth: true
                }
            }

            Card { objectName: "dataSettingsCard"; title: page.tr("settings.data")
                Label { Layout.fillWidth: true; text: page.tr("settings.data_help"); color: Tokens.Theme.textSecondary; wrapMode: Text.WordWrap }
                RowLayout {
                    IzlekButton { objectName: "exportDataButton"; text: page.tr("settings.export"); enabled: !page.transferModelController.busy; onClicked: exportDialog.open() }
                    IzlekButton { objectName: "selectImportButton"; text: page.tr("settings.import"); variant: "secondary"; enabled: !page.transferModelController.busy; onClicked: importDialog.open() }
                }
                Label { visible: page.transferModelController.busy; text: page.tr("common.working"); color: Tokens.Theme.textMuted }
                Label { objectName: "transferFeedback"; visible: page.transferModelController.feedback.length > 0; text: page.transferModelController.feedback; color: page.transferModelController.feedbackKind === "danger" ? Tokens.Theme.danger : Tokens.Theme.success; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Rectangle { objectName: "importPreview"; visible: Object.keys(page.transferModelController.preview).length > 0; Layout.fillWidth: true; implicitHeight: preview.implicitHeight + 2 * Tokens.Theme.spaceMd; color: Tokens.Theme.surfaceElevated; radius: Tokens.Theme.radiusMd; border.color: Tokens.Theme.border
                    ColumnLayout {
                        id: preview
                        anchors.fill: parent
                        anchors.margins: Tokens.Theme.spaceMd
                        Label { text: page.tr("settings.import_summary"); color: Tokens.Theme.textPrimary }
                        Label {
                            text: i18n.t("settings.import_counts").replace("{movies}", page.transferModelController.preview.movies || 0).replace("{shows}", page.transferModelController.preview.shows || 0).replace("{episodes}", page.transferModelController.preview.episode_progress || 0)
                            color: Tokens.Theme.textSecondary
                        }
                        IzlekButton { objectName: "confirmImportButton"; text: page.tr("settings.import"); onClicked: page.transferModelController.importSelected() }
                    }
                }
            }

            Card { objectName: "cacheSettingsCard"; title: page.tr("settings.cache")
                Label { Layout.fillWidth: true; text: page.tr("settings.cache_help"); color: Tokens.Theme.textMuted; wrapMode: Text.WordWrap }
                Label { text: i18n.tf("settings.cache_size", cacheController.sizeLabel); color: Tokens.Theme.textSecondary }
                RowLayout {
                    IzlekButton { objectName: "refreshCacheButton"; text: page.tr("common.refresh"); variant: "secondary"; enabled: !cacheController.busy; onClicked: cacheController.refresh() }
                    IzlekButton { objectName: "clearCacheButton"; text: page.tr("settings.cache_clear"); enabled: !cacheController.busy; onClicked: cacheController.clear() }
                }
                Label { visible: cacheController.feedback.length > 0; text: cacheController.feedback; color: cacheController.feedbackKind === "danger" ? Tokens.Theme.danger : Tokens.Theme.success; wrapMode: Text.WordWrap }
            }

            Card { objectName: "hiddenMediaSettingsCard"; title: page.tr("settings.hidden")
                Label { Layout.fillWidth: true; text: page.tr("settings.hidden_help"); color: Tokens.Theme.textSecondary; wrapMode: Text.WordWrap }
                Label { visible: personalController.hiddenItems.length === 0; text: page.tr("settings.hidden_empty"); color: Tokens.Theme.textMuted }
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
                        Label {
                            Layout.fillWidth: true
                            text: modelData.mediaType === "movie"
                                  ? i18n.tf("settings.media_movie", modelData.title)
                                  : i18n.tf("settings.media_show", modelData.title)
                            elide: Text.ElideRight
                            color: Tokens.Theme.textPrimary
                        }
                        IzlekButton { objectName: "restoreHiddenMediaButton"; text: page.tr("settings.restore"); variant: "secondary"; enabled: !personalController.busy; onClicked: personalController.setDismissed(modelData, false) }
                    }
                    ScrollBar.vertical: ScrollBar {}
                }
                Label { visible: !!personalController.feedback; text: personalController.feedback; color: Tokens.Theme.textSecondary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            }
            Card { objectName: "shortcutsSettingsCard"; title: page.tr("settings.shortcuts")
                Repeater {
                    model: [
                        page.tr("settings.shortcut_search"),
                        page.tr("settings.shortcut_home"),
                        page.tr("settings.shortcut_movies"),
                        page.tr("settings.shortcut_shows"),
                        page.tr("settings.shortcut_lists"),
                        page.tr("settings.shortcut_stats"),
                        page.tr("settings.shortcut_settings"),
                        page.tr("settings.shortcut_esc")
                    ]
                    delegate: Label { text: modelData; color: Tokens.Theme.textSecondary }
                }
            }
            Card { objectName: "aboutSettingsCard"; title: page.tr("settings.about")
                Image { objectName: "tmdbLogo"; source: "../../../resources/images/tmdb.svg"; Layout.preferredWidth: 116; Layout.preferredHeight: 16; fillMode: Image.PreserveAspectFit; Accessible.name: "The Movie Database (TMDB)" }
                Label { text: i18n.tf("settings.about_version", appVersion); color: Tokens.Theme.textSecondary }
                Label { text: "GPL-3.0-or-later"; color: Tokens.Theme.textSecondary }
                Label { objectName: "tmdbDataSourceLabel"; Layout.fillWidth: true; text: page.tr("settings.tmdb_data"); color: Tokens.Theme.textMuted; wrapMode: Text.WordWrap }
                Label { objectName: "tmdbAttributionNotice"; Layout.fillWidth: true; text: page.tr("settings.tmdb_notice"); color: Tokens.Theme.textSecondary; wrapMode: Text.WordWrap }
                Label { objectName: "justWatchAttributionLabel"; Layout.fillWidth: true; text: page.tr("settings.justwatch"); color: Tokens.Theme.textMuted; wrapMode: Text.WordWrap }
                IzlekButton { objectName: "tmdbWebsiteButton"; text: "TMDB"; variant: "secondary"; onClicked: Qt.openUrlExternally("https://www.themoviedb.org") }
                IzlekButton { objectName: "githubButton"; text: "GitHub"; variant: "secondary"; onClicked: Qt.openUrlExternally("https://github.com/Teknoloji-Filozoflari/Izlek") }
            }
            Item { Layout.preferredHeight: Tokens.Theme.spaceLg }
        }
    }
    FileDialog {
        id: exportDialog
        objectName: "exportFileDialog"
        title: page.tr("settings.export_title")
        fileMode: FileDialog.SaveFile
        nameFilters: [page.tr("settings.filter_izlek_json")]
        defaultSuffix: "json"
        onAccepted: page.transferModelController.exportTo(selectedFile.toString())
    }
    FileDialog {
        id: importDialog
        objectName: "importFileDialog"
        title: page.tr("settings.import_title")
        fileMode: FileDialog.OpenFile
        nameFilters: [page.tr("settings.filter_izlek_json"), page.tr("settings.filter_json")]
        onAccepted: page.transferModelController.previewImport(selectedFile.toString())
    }
}
