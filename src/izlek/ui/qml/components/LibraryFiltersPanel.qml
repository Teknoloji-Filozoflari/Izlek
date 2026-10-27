import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Rectangle {
    id: panel
    property var controller
    property string kind: "movie"
    property string selectedGenre: controller.filterValues.genre || ""
    readonly property bool filterPopupOpen: state.popup.visible || genre.popup.visible
    signal applied()
    implicitHeight: body.implicitHeight + 2 * Tokens.Theme.spaceMd
    color: Tokens.Theme.surface
    radius: Tokens.Theme.radiusMd
    border.color: Tokens.Theme.border
    ColumnLayout {
        id: body
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceMd
        spacing: Tokens.Theme.spaceSm
        GridLayout {
            Layout.fillWidth: true
            columns: width >= 900 ? 6 : width >= 600 ? 3 : 2
            columnSpacing: Tokens.Theme.spaceSm
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: (i18n.revision, i18n.t("library.filter_status")); color: Tokens.Theme.textSecondary }
                FilterComboBox {
                    id: state
                    objectName: "libraryStatusFilter"
                    Layout.fillWidth: true
                    model: [(i18n.revision, i18n.t("status.all")), (i18n.revision, i18n.t("status.planned")), (i18n.revision, i18n.t("status.watching")), (i18n.revision, i18n.t("status.watched"))]
                    currentIndex: ["", "PLANNED", "WATCHING", "WATCHED"].indexOf(panel.controller.filterValues.status || "")
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: (i18n.revision, i18n.t("library.filter_genre")); color: Tokens.Theme.textSecondary }
                FilterComboBox {
                    id: genre
                    objectName: "libraryGenreFilter"
                    Layout.fillWidth: true
                    model: ["Tüm türler"].concat(panel.controller.genres)
                    currentIndex: Math.max(0, model.indexOf(panel.selectedGenre))
                    onActivated: panel.selectedGenre = currentIndex > 0 ? currentText : ""
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: (i18n.revision, i18n.t("library.year_from")); color: Tokens.Theme.textSecondary }
                FilterTextField {
                    id: yearFrom
                    objectName: "libraryYearFromFilter"
                    Layout.fillWidth: true
                    text: panel.controller.filterValues.year_from || ""
                    placeholderText: (i18n.revision, i18n.t("library.year_from_ph"))
                    validator: IntValidator { bottom: 1888; top: 2100 }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: (i18n.revision, i18n.t("library.year_to")); color: Tokens.Theme.textSecondary }
                FilterTextField {
                    id: yearTo
                    objectName: "libraryYearToFilter"
                    Layout.fillWidth: true
                    text: panel.controller.filterValues.year_to || ""
                    placeholderText: (i18n.revision, i18n.t("library.year_to_ph"))
                    validator: IntValidator { bottom: 1888; top: 2100 }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: panel.kind === "tv" ? "En fazla bölüm süresi" : "En fazla süre"; color: Tokens.Theme.textSecondary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                FilterTextField {
                    id: runtime
                    objectName: "libraryRuntimeFilter"
                    Layout.fillWidth: true
                    text: panel.controller.filterValues.max_runtime || ""
                    placeholderText: (i18n.revision, i18n.t("library.runtime_ph"))
                    validator: IntValidator { bottom: 0; top: 1440 }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: (i18n.revision, i18n.t("library.min_score")); color: Tokens.Theme.textSecondary }
                FilterSpinBox {
                    id: score
                    objectName: "libraryScoreFilter"
                    Layout.fillWidth: true
                    from: 0; to: 100; stepSize: 5
                    value: Math.round((panel.controller.filterValues.min_score || 0) * 10)
                    textFromValue: function(value) { return (value / 10).toFixed(1) }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label {
                Layout.fillWidth: true
                text: (i18n.revision, i18n.t("library.filter_note"))
                color: Tokens.Theme.textMuted
                wrapMode: Text.WordWrap
            }
            IzlekButton {
                objectName: "applyLibraryFiltersButton"
                text: (i18n.revision, i18n.t("common.apply"))
                enabled: !panel.controller.batchBusy
                onClicked: {
                    panel.controller.applyFilters({status: ["", "PLANNED", "WATCHING", "WATCHED"][state.currentIndex], genre: panel.selectedGenre, year_from: yearFrom.text, year_to: yearTo.text, max_runtime: runtime.text, min_score: score.value / 10})
                    panel.applied()
                }
            }
            IzlekButton {
                objectName: "clearLibraryFiltersButton"
                text: (i18n.revision, i18n.t("common.clear"))
                variant: "secondary"
                enabled: !panel.controller.batchBusy
                onClicked: {
                    state.currentIndex = 0
                    panel.selectedGenre = ""
                    yearFrom.text = ""; yearTo.text = ""; runtime.text = ""; score.value = 0
                    panel.controller.applyFilters({})
                    panel.applied()
                }
            }
        }
    }
}
