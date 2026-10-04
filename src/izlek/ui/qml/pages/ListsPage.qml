import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property string pageTitle: "Listeler"
    property var controller
    readonly property bool filterPopupOpen: mediaPicker.popup.visible
    signal mediaSelected(string kind, int tmdbId)
    color: Tokens.Theme.background

    Component.onCompleted: controller.refresh()
    onVisibleChanged: { if (visible) controller.refresh() }

    RowLayout {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceLg
        spacing: Tokens.Theme.spaceMd

        Rectangle {
            Layout.preferredWidth: Math.min(280, page.width * 0.35)
            Layout.fillHeight: true
            color: Tokens.Theme.surface
            radius: Tokens.Theme.radiusMd
            border.color: Tokens.Theme.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Tokens.Theme.spaceMd
                spacing: Tokens.Theme.spaceSm
                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: "Listeler"
                        color: Tokens.Theme.textPrimary
                        font.pixelSize: Tokens.Theme.textHeading
                        font.weight: Tokens.Theme.weightDemiBold
                    }
                    Item { Layout.fillWidth: true }
                    IzlekButton {
                        objectName: "createListButton"
                        text: "+ Yeni"
                        enabled: !controller.busy
                        onClicked: page.openNameDialog(false)
                    }
                }
                Label {
                    visible: controller.lists.length === 0
                    Layout.fillWidth: true
                    text: "Henüz listen yok. Yeni liste oluştur."
                    color: Tokens.Theme.textSecondary
                    wrapMode: Text.WordWrap
                }
                ListView {
                    id: listsView
                    objectName: "customListsView"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: controller.lists
                    clip: true
                    spacing: Tokens.Theme.spaceXs
                    delegate: ItemDelegate {
                        required property var modelData
                        required property int index
                        width: listsView.width
                        height: Tokens.Theme.controlHeight + Tokens.Theme.spaceSm
                        onClicked: controller.selectList(modelData.id)
                        background: Rectangle {
                            color: modelData.id === controller.selectedId
                                   ? Tokens.Theme.accentSurface
                                   : parent.hovered ? Tokens.Theme.hoverSurface
                                                    : Tokens.Theme.surfaceElevated
                            radius: Tokens.Theme.radiusSm
                        }
                        contentItem: RowLayout {
                            Label {
                                Layout.fillWidth: true
                                text: modelData.name + " (" + modelData.count + ")"
                                color: Tokens.Theme.textPrimary
                                elide: Text.ElideRight
                            }
                            IzlekButton {
                                text: "↑"
                                variant: "ghost"
                                Layout.preferredWidth: 34
                                enabled: index > 0 && !controller.busy
                                Accessible.name: modelData.name + " yukarı taşı"
                                onClicked: controller.moveList(modelData.id, -1)
                            }
                            IzlekButton {
                                text: "↓"
                                variant: "ghost"
                                Layout.preferredWidth: 34
                                enabled: index < controller.lists.length - 1
                                         && !controller.busy
                                Accessible.name: modelData.name + " aşağı taşı"
                                onClicked: controller.moveList(modelData.id, 1)
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Tokens.Theme.surface
            radius: Tokens.Theme.radiusMd
            border.color: Tokens.Theme.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Tokens.Theme.spaceLg
                spacing: Tokens.Theme.spaceMd
                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: page.selectedName()
                        color: Tokens.Theme.textPrimary
                        font.pixelSize: Tokens.Theme.textHeading
                        font.weight: Tokens.Theme.weightDemiBold
                        elide: Text.ElideRight
                    }
                    IzlekButton {
                        objectName: "renameListButton"
                        text: "Yeniden Adlandır"
                        variant: "secondary"
                        enabled: controller.selectedId > 0 && !controller.busy
                        onClicked: page.openNameDialog(true)
                    }
                    IzlekButton {
                        objectName: "deleteListButton"
                        text: "Sil"
                        variant: "danger"
                        enabled: controller.selectedId > 0 && !controller.busy
                        onClicked: deleteDialog.open()
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    visible: controller.selectedId > 0
                    TextField {
                        id: mediaSearchInput
                        objectName: "listMediaSearchInput"
                        Layout.fillWidth: true
                        placeholderText: "Kütüphanede başlığa göre ara"
                        Accessible.name: "Kütüphanede medya ara"
                        color: Tokens.Theme.textPrimary
                        onAccepted: controller.searchCandidates(text)
                        background: Rectangle {
                            color: Tokens.Theme.surfaceElevated
                            radius: Tokens.Theme.radiusSm
                            border.color: mediaSearchInput.activeFocus
                                          ? Tokens.Theme.accent : Tokens.Theme.border
                        }
                    }
                    IzlekButton {
                        objectName: "searchListMediaButton"
                        text: "Ara"
                        enabled: !controller.busy
                        onClicked: controller.searchCandidates(mediaSearchInput.text)
                    }
                    IzlekButton {
                        objectName: "clearListMediaSearchButton"
                        text: "Temizle"
                        variant: "secondary"
                        onClicked: {
                            mediaSearchInput.clear()
                            controller.searchCandidates("")
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    visible: controller.selectedId > 0
                    FilterComboBox {
                        id: mediaPicker
                        objectName: "listMediaPicker"
                        Layout.fillWidth: true
                        model: controller.candidates
                        textRole: "display_title"
                        enabled: count > 0 && !controller.busy
                        Accessible.name: "Yerel medya seç"
                    }
                    IzlekButton {
                        objectName: "addMediaToListButton"
                        text: "Medya Ekle"
                        enabled: mediaPicker.currentIndex >= 0
                                 && mediaPicker.count > 0 && !controller.busy
                        onClicked: {
                            var item = controller.candidates[mediaPicker.currentIndex]
                            if (item) controller.addMedia(controller.selectedId,
                                                          item.kind, item.tmdb_id)
                        }
                    }
                }
                Label {
                    visible: controller.selectedId > 0
                             && controller.candidates.length === 0
                    text: "Eklenebilecek içerik bulunamadı. Aramayı temizle veya kütüphanene içerik ekle."
                    color: Tokens.Theme.textMuted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Label {
                    visible: !!controller.error
                    text: controller.error
                    color: Tokens.Theme.danger
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
                EmptyState {
                    visible: controller.lists.length === 0
                             || (controller.selectedId > 0 && controller.items.length === 0)
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: controller.lists.length === 0 ? "Liste oluştur" : "Liste boş"
                    description: controller.lists.length === 0
                                 ? "Filmlerini ve dizilerini kendi listelerinde düzenle."
                                 : "Yerel medya ekle veya detay sayfasındaki Listeye Ekle düğmesini kullan."
                }
                ListView {
                    id: mediaView
                    objectName: "customListMedia"
                    visible: controller.items.length > 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: controller.items
                    clip: true
                    spacing: Tokens.Theme.spaceSm
                    delegate: Rectangle {
                        required property var modelData
                        required property int index
                        width: mediaView.width
                        height: 72
                        color: Tokens.Theme.surfaceElevated
                        radius: Tokens.Theme.radiusSm
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Tokens.Theme.spaceSm
                            spacing: Tokens.Theme.spaceSm
                            Image {
                                objectName: "customListPoster"
                                Layout.preferredWidth: 36
                                Layout.preferredHeight: 54
                                source: modelData.poster || ""
                                asynchronous: true
                                fillMode: Image.PreserveAspectFit
                                sourceSize.width: 72
                                sourceSize.height: 108
                            }
                            ItemDelegate {
                                Layout.fillWidth: true
                                text: modelData.title + " · "
                                      + (modelData.kind === "movie" ? "Film" : "Dizi")
                                      + (modelData.year ? " · " + modelData.year : "")
                                onClicked: page.mediaSelected(modelData.kind,
                                                              modelData.tmdb_id)
                                contentItem: Label {
                                    text: parent.text
                                    color: Tokens.Theme.textPrimary
                                    elide: Text.ElideRight
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Item {}
                            }
                            IzlekButton {
                                text: "↑"
                                variant: "ghost"
                                Layout.preferredWidth: 34
                                enabled: index > 0 && !controller.busy
                                Accessible.name: modelData.title + " yukarı taşı"
                                onClicked: controller.moveMedia(controller.selectedId,
                                                                modelData.kind,
                                                                modelData.tmdb_id, -1)
                            }
                            IzlekButton {
                                text: "↓"
                                variant: "ghost"
                                Layout.preferredWidth: 34
                                enabled: index < controller.items.length - 1
                                         && !controller.busy
                                Accessible.name: modelData.title + " aşağı taşı"
                                onClicked: controller.moveMedia(controller.selectedId,
                                                                modelData.kind,
                                                                modelData.tmdb_id, 1)
                            }
                            IzlekButton {
                                text: "Çıkar"
                                variant: "danger"
                                Layout.preferredWidth: 68
                                enabled: !controller.busy
                                onClicked: controller.removeMedia(controller.selectedId,
                                                                  modelData.kind,
                                                                  modelData.tmdb_id)
                            }
                        }
                    }
                }
            }
        }
    }

    function selectedName() {
        for (var i = 0; i < controller.lists.length; i++)
            if (controller.lists[i].id === controller.selectedId)
                return controller.lists[i].name
        return "Liste seç"
    }
    function openNameDialog(editing) {
        nameDialog.editing = editing
        nameInput.text = editing ? selectedName() : ""
        nameDialog.open()
    }

    Dialog {
        id: nameDialog
        objectName: "listNameDialog"
        property bool editing: false
        modal: true
        focus: true
        title: editing ? "Listeyi Yeniden Adlandır" : "Yeni Liste"
        width: Math.min(400, page.width - 2 * Tokens.Theme.spaceLg)
        x: (page.width - width) / 2
        y: (page.height - height) / 2
        closePolicy: Popup.CloseOnEscape
        onOpened: nameInput.forceActiveFocus()
        contentItem: ColumnLayout {
            spacing: Tokens.Theme.spaceMd
            TextField {
                id: nameInput
                objectName: "listNameInput"
                Layout.fillWidth: true
                placeholderText: "Liste adı"
                color: Tokens.Theme.textPrimary
                maximumLength: 200
                onAccepted: nameDialog.save()
            }
            IzlekButton {
                text: nameDialog.editing ? "Kaydet" : "Oluştur"
                enabled: nameInput.text.trim().length > 0
                onClicked: nameDialog.save()
            }
        }
        function save() {
            if (!nameInput.text.trim().length) return
            if (editing) controller.renameList(controller.selectedId, nameInput.text)
            else controller.createList(nameInput.text)
            close()
        }
        background: Rectangle {
            color: Tokens.Theme.surfaceElevated
            radius: Tokens.Theme.radiusMd
            border.color: Tokens.Theme.border
        }
    }
    IzlekDialog {
        id: deleteDialog
        objectName: "deleteListDialog"
        title: "Listeyi Sil"
        message: "Bu liste ve üyelikleri silinsin mi? Medyalar kütüphanede kalır."
        confirmText: "Sil"
        onConfirmed: controller.deleteList(controller.selectedId)
    }
}
