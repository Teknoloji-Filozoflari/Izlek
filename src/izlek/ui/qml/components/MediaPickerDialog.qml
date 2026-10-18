import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "." as Components
import "../theme" as Tokens

Dialog {
    id: picker
    objectName: "mediaPickerDialog"
    property var controller
    property int listId: 0
    property var selections: ({})
    readonly property int selectionCount: Object.keys(selections).length
    parent: Overlay.overlay
    width: Math.min(700, parent.width - 2 * Tokens.Theme.spaceLg)
    height: Math.min(650, parent.height - 2 * Tokens.Theme.spaceLg)
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    modal: true
    focus: true
    padding: Tokens.Theme.spaceLg
    closePolicy: Popup.CloseOnEscape
    onOpened: {
        selections = ({})
        search.text = ""
        controller.searchCandidates("")
        search.forceActiveFocus()
    }
    onClosed: controller.searchCandidates("")
    function toggle(item) {
        var key = item.kind + ":" + item.tmdb_id
        var next = Object.assign({}, selections)
        if (next[key]) delete next[key]
        else next[key] = { kind: item.kind, tmdb_id: item.tmdb_id }
        selections = next
    }
    background: Rectangle {
        color: Tokens.Theme.surface
        radius: Tokens.Theme.radiusLg
        border.color: Tokens.Theme.border
    }
    contentItem: ColumnLayout {
        spacing: Tokens.Theme.spaceMd
        Keys.onEscapePressed: function(event) {
            picker.close()
            event.accepted = true
        }
        Label {
            text: "Listene içerik ekle"
            color: Tokens.Theme.textPrimary
            font.pixelSize: Tokens.Theme.textHeading
        }
        Components.SearchField {
            id: search
            objectName: "listMediaSearchInput"
            Layout.fillWidth: true
            Layout.preferredHeight: Tokens.Theme.controlHeight + 4
            placeholderText: "Film veya dizi ara"
            onTextChanged: picker.controller.searchCandidates(text)
            Keys.onEscapePressed: function(event) {
                picker.close()
                event.accepted = true
            }
        }
        Label {
            Layout.fillWidth: true
            text: picker.selectionCount + " içerik seçildi · Aramayı değiştirince seçimlerin korunur"
            color: Tokens.Theme.textSecondary
            wrapMode: Text.WordWrap
        }
        ListView {
            id: candidates
            objectName: "mediaPickerCandidates"
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: picker.visible ? picker.controller.candidates : []
            clip: true
            spacing: Tokens.Theme.spaceXs
            delegate: CheckDelegate {
                id: option
                required property var modelData
                objectName: "mediaPickerOption"
                property string resolvedPoster: modelData.poster || ""
                width: candidates.width
                height: 82
                checked: !!picker.selections[modelData.kind + ":" + modelData.tmdb_id]
                hoverEnabled: true
                text: modelData.display_title
                Accessible.name: text
                onClicked: picker.toggle(modelData)
                Component.onCompleted: picker.controller.requestCandidatePoster(modelData.kind, modelData.tmdb_id)
                onModelDataChanged: {
                    resolvedPoster = modelData.poster || ""
                    picker.controller.requestCandidatePoster(modelData.kind, modelData.tmdb_id)
                }
                indicator: Rectangle {
                    width: 22
                    height: 22
                    x: option.width - width - Tokens.Theme.spaceMd
                    y: (option.height - height) / 2
                    radius: Tokens.Theme.radiusSm
                    color: option.checked ? Tokens.Theme.accent : Tokens.Theme.surface
                    border.color: option.checked ? Tokens.Theme.accent : Tokens.Theme.border
                    Text {
                        anchors.centerIn: parent
                        text: option.checked ? "✓" : ""
                        color: Tokens.Theme.textPrimary
                        font.pixelSize: Tokens.Theme.textBody
                    }
                }
                Connections {
                    target: picker.controller
                    function onCandidatePosterAvailable(kind, tmdbId, url) {
                        if (kind === option.modelData.kind && tmdbId === option.modelData.tmdb_id)
                            option.resolvedPoster = url
                    }
                }
                contentItem: RowLayout {
                    spacing: Tokens.Theme.spaceMd
                    Image {
                        Layout.preferredWidth: 42
                        Layout.preferredHeight: 63
                        source: option.resolvedPoster || Qt.resolvedUrl("../../../resources/images/poster-placeholder.svg")
                        asynchronous: true
                        fillMode: Image.PreserveAspectFit
                        sourceSize.width: 84
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Label {
                            Layout.fillWidth: true
                            text: option.modelData.title
                            color: Tokens.Theme.textPrimary
                            elide: Text.ElideRight
                        }
                        Label {
                            text: (option.modelData.kind === "movie" ? "Film" : "Dizi")
                                  + (option.modelData.year ? " · " + option.modelData.year : "")
                            color: Tokens.Theme.textSecondary
                        }
                    }
                    Item { Layout.preferredWidth: Tokens.Theme.controlHeight }
                }
                background: Rectangle {
                    radius: Tokens.Theme.radiusSm
                    color: option.checked ? Tokens.Theme.accentSurface
                           : option.hovered ? Tokens.Theme.hoverSurface : Tokens.Theme.surfaceElevated
                    border.color: option.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
                }
            }
            ScrollBar.vertical: ScrollBar {}
        }
        Label {
            visible: picker.controller.candidates.length === 0
            text: "Eklenebilecek içerik bulunamadı."
            color: Tokens.Theme.textMuted
        }
        Label {
            Layout.fillWidth: true
            visible: !!picker.controller.error
            text: picker.controller.error
            color: Tokens.Theme.danger
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.fillWidth: true
            IzlekButton {
                text: "Seçimi temizle"
                variant: "ghost"
                enabled: picker.selectionCount > 0 && !picker.controller.busy
                onClicked: picker.selections = ({})
            }
            Item { Layout.fillWidth: true }
            IzlekButton {
                text: "Vazgeç"
                variant: "secondary"
                enabled: !picker.controller.busy
                onClicked: picker.close()
            }
            IzlekButton {
                objectName: "confirmAddMediaButton"
                text: "Seçilenleri Ekle (" + picker.selectionCount + ")"
                enabled: picker.selectionCount > 0 && !picker.controller.busy
                onClicked: picker.controller.addMany(picker.listId, Object.values(picker.selections))
            }
        }
    }
    Connections {
        target: picker.controller
        function onBatchAdded(listId) { if (listId === picker.listId) picker.close() }
    }
}
