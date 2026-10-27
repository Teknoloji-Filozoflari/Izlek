import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Dialog {
    id: dialog
    property var controller
    property var selectedIds: []
    parent: Overlay.overlay
    modal: true
    focus: true
    padding: Tokens.Theme.spaceLg
    width: Math.min(460, parent.width - 2 * Tokens.Theme.spaceLg)
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    closePolicy: controller.batchBusy ? Popup.NoAutoClose : Popup.CloseOnEscape
    background: Rectangle { color: Tokens.Theme.surface; radius: Tokens.Theme.radiusLg; border.color: Tokens.Theme.border }
    function apply() { controller.batchApply(selectedIds, action.currentValue, Number(list.currentValue || 0)) }
    contentItem: ColumnLayout {
        spacing: Tokens.Theme.spaceMd
        Label { text: "Toplu işlem · " + dialog.selectedIds.length + " içerik"; color: Tokens.Theme.textPrimary; font.pixelSize: Tokens.Theme.textEmpty }
        FilterComboBox {
            id: action
            objectName: "libraryBatchAction"
            Layout.fillWidth: true
            model: [
                {text: (i18n.revision, i18n.t("status.make_watched")), value: "WATCHED"},
                {text: (i18n.revision, i18n.t("status.make_watching")), value: "WATCHING"},
                {text: (i18n.revision, i18n.t("status.make_planned")), value: "PLANNED"},
                {text: (i18n.revision, i18n.t("library.add_favorite")), value: "favorite"},
                {text: (i18n.revision, i18n.t("library.remove_favorite")), value: "unfavorite"},
                {text: (i18n.revision, i18n.t("library.add_to_list")), value: "list"}
            ]
            textRole: "text"; valueRole: "value"
            enabled: !dialog.controller.batchBusy
        }
        FilterComboBox {
            id: list
            objectName: "libraryBatchList"
            visible: action.currentValue === "list"
            Layout.fillWidth: true
            model: dialog.controller.availableLists
            textRole: "name"; valueRole: "id"
            enabled: !dialog.controller.batchBusy
        }
        Label {
            Layout.fillWidth: true
            visible: action.currentValue === "list" && list.count === 0
            text: (i18n.revision, i18n.t("library.need_list"))
            color: Tokens.Theme.textMuted
            wrapMode: Text.WordWrap
        }
        Label {
            Layout.fillWidth: true
            visible: !!dialog.controller.error
            text: dialog.controller.error
            color: Tokens.Theme.danger
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Item { Layout.fillWidth: true }
            IzlekButton { text: (i18n.revision, i18n.t("common.cancel")); variant: "secondary"; enabled: !dialog.controller.batchBusy; onClicked: dialog.close() }
            IzlekButton {
                objectName: "applyLibraryBatchButton"
                text: dialog.controller.batchBusy ? "Kaydediliyor…" : "Uygula"
                enabled: dialog.selectedIds.length > 0 && !dialog.controller.batchBusy && (action.currentValue !== "list" || list.count > 0)
                onClicked: {
                    if (["PLANNED", "WATCHING", "WATCHED"].indexOf(action.currentValue) >= 0) confirm.open()
                    else dialog.apply()
                }
            }
        }
    }
    IzlekDialog {
        id: confirm
        objectName: "libraryBatchConfirm"
        parent: Overlay.overlay
        title: (i18n.revision, i18n.t("library.bulk_status_title"))
        message: dialog.selectedIds.length + " içerik için “" + action.currentText + "” işlemi uygulanacak. Dizilerde bölüm işaretleri değişmez."
        confirmText: "Seçilenlere uygula"
        onConfirmed: dialog.apply()
    }
    Connections {
        target: dialog.controller
        function onBulkCompleted(count) { dialog.close() }
    }
}
