import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property string pageTitle: "Listeler"
    property var controller
    readonly property bool filterPopupOpen: mediaPicker.visible
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
                    visible: !page.hasCustomLists()
                    Layout.fillWidth: true
                    text: "Akıllı listeler otomatik dolar. Özel liste için Yeni’ye bas."
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
                            ReorderHandle {
                                id: listHandle
                                objectName: "listReorderHandle"
                                visible: !modelData.smart
                                enabled: !controller.busy && !modelData.smart
                                label: modelData.name
                                onDropped: function(position) {
                                    var point = listsView.mapFromItem(null, position.x, position.y)
                                    if (point.y < 0 || point.y >= listsView.height) return
                                    var target = listsView.indexAt(point.x + listsView.contentX, point.y + listsView.contentY)
                                    if (target >= 0 && !controller.lists[target].smart)
                                        controller.reorderList(modelData.id, controller.lists[target].id)
                                }
                                ReorderAutoScroll {
                                    view: listsView
                                    active: listHandle.dragging
                                    scenePosition: listHandle.scenePosition
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: modelData.name + " (" + modelData.count + ")"
                                color: Tokens.Theme.textPrimary
                                elide: Text.ElideRight
                            }
                            Badge {
                                visible: !!modelData.smart
                                text: "Akıllı"
                                tone: "accent"
                                Accessible.name: modelData.name + " akıllı liste"
                            }
                            IzlekButton {
                                text: "↑"
                                variant: "ghost"
                                Layout.preferredWidth: 34
                                visible: !modelData.smart
                                enabled: page.canMoveCustom(index, -1) && !controller.busy
                                Accessible.name: modelData.name + " yukarı taşı"
                                onClicked: controller.moveList(modelData.id, -1)
                            }
                            IzlekButton {
                                text: "↓"
                                variant: "ghost"
                                Layout.preferredWidth: 34
                                visible: !modelData.smart
                                enabled: page.canMoveCustom(index, 1) && !controller.busy
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
                        enabled: controller.selectedId > 0 && !controller.selectedIsSmart && !controller.busy
                        onClicked: page.openNameDialog(true)
                    }
                    IzlekButton {
                        objectName: "deleteListButton"
                        text: "Sil"
                        variant: "danger"
                        enabled: controller.selectedId > 0 && !controller.selectedIsSmart && !controller.busy
                        onClicked: deleteDialog.open()
                    }
                }
                Label {
                    objectName: "smartListDescription"
                    visible: controller.selectedIsSmart && controller.selectedDescription.length > 0
                    Layout.fillWidth: true
                    text: controller.selectedDescription
                    color: Tokens.Theme.textSecondary
                    wrapMode: Text.WordWrap
                }
                RowLayout {
                    Layout.fillWidth: true
                    visible: controller.selectedId > 0 && !controller.selectedIsSmart
                    IzlekButton {
                        objectName: "addMediaToListButton"
                        text: "+ İçerik Ekle"
                        enabled: !controller.busy
                        onClicked: {
                            mediaPicker.listId = controller.selectedId
                            mediaPicker.open()
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        text: "Tutamaçları sürükleyerek sırala"
                        color: Tokens.Theme.textMuted
                        elide: Text.ElideRight
                    }
                }
                Label {
                    visible: !!controller.error
                    text: controller.error
                    color: Tokens.Theme.danger
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
                EmptyState {
                    visible: controller.selectedId !== 0 && controller.items.length === 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: controller.selectedIsSmart ? "Akıllı liste boş" : "Liste boş"
                    description: controller.selectedIsSmart
                                 ? "Koşullara uyan içerik yok. Favori, durum veya etiket ekleyince dolar."
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
                            ReorderHandle {
                                id: mediaHandle
                                objectName: "listMediaReorderHandle"
                                visible: !controller.selectedIsSmart
                                enabled: !controller.busy && !controller.selectedIsSmart
                                label: modelData.title
                                onDropped: function(position) {
                                    var point = mediaView.mapFromItem(null, position.x, position.y)
                                    if (point.y < 0 || point.y >= mediaView.height) return
                                    var target = mediaView.indexAt(point.x + mediaView.contentX, point.y + mediaView.contentY)
                                    if (target >= 0) {
                                        var item = controller.items[target]
                                        controller.reorderMedia(controller.selectedId, modelData.kind,
                                            modelData.tmdb_id, item.kind, item.tmdb_id)
                                    }
                                }
                                ReorderAutoScroll {
                                    view: mediaView
                                    active: mediaHandle.dragging
                                    scenePosition: mediaHandle.scenePosition
                                }
                            }
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
                            Badge {
                                objectName: "customListStatus"
                                text: modelData.status_label || "İzlenmedi"
                                tone: modelData.watched ? "success"
                                      : modelData.status === "WATCHING" ? "accent" : "neutral"
                                Accessible.name: modelData.title + ": " + text
                            }
                            IzlekButton {
                                text: "↑"
                                variant: "ghost"
                                Layout.preferredWidth: 34
                                visible: !controller.selectedIsSmart
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
                                visible: !controller.selectedIsSmart
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
                                visible: !controller.selectedIsSmart
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

    MediaPickerDialog {
        id: mediaPicker
        controller: page.controller
    }

    function hasCustomLists() {
        for (var i = 0; i < controller.lists.length; i++)
            if (!controller.lists[i].smart) return true
        return false
    }
    function canMoveCustom(index, direction) {
        var next = index + direction
        if (next < 0 || next >= controller.lists.length) return false
        return !controller.lists[index].smart && !controller.lists[next].smart
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
            FilterTextField {
                id: nameInput
                objectName: "listNameInput"
                Layout.fillWidth: true
                placeholderText: "Liste adı"
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
