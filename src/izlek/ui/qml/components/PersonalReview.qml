import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

ColumnLayout {
    id: editor
    property string kind: "movie"
    property int mediaId: 0
    property string mediaTitle: ""
    property var backend: personalController
    property bool expanded: false
    property bool ready: false
    property bool dirty: false
    property bool syncing: false
    readonly property bool matching: backend.current.kind === kind && backend.current.id === mediaId
    readonly property bool filterPopupOpen: rating.popup.visible
    visible: expanded
    spacing: Tokens.Theme.spaceSm
    function load() { if (ready && mediaId > 0) backend.load(kind, mediaId) }
    function syncDraft() {
        syncing = true
        rating.currentIndex = backend.current.rating || 0
        note.text = backend.current.note || ""
        syncing = false
    }
    Component.onCompleted: { ready = true; load(); loadTags() }
    onVisibleChanged: if (visible && !matching) load()
    onMediaIdChanged: { expanded = false; dirty = false; load(); loadTags() }
    onKindChanged: { expanded = false; dirty = false; load(); loadTags() }
    function loadTags() {
        if (ready && mediaId > 0) tagsController.loadForMedia(kind, mediaId)
    }
    Connections {
        target: editor.backend
        function onRecordLoaded(kind, itemId) {
            if (kind !== editor.kind || itemId !== editor.mediaId || editor.dirty) return
            editor.syncDraft()
        }
        function onReviewSaved(kind, itemId) {
            if (kind !== editor.kind || itemId !== editor.mediaId || !editor.matching) return
            editor.dirty = false
            editor.syncDraft()
        }
    }
    Connections {
        target: tagsController
        function onMediaTagsChanged(kind, itemId) {
            if (kind !== editor.kind || itemId !== editor.mediaId) return
            tagInput.text = ""
        }
    }
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: body.implicitHeight + 2 * Tokens.Theme.spaceMd
        color: Tokens.Theme.surface
        radius: Tokens.Theme.radiusMd
        border.color: Tokens.Theme.border
        ColumnLayout {
            id: body
            anchors.fill: parent
            anchors.margins: Tokens.Theme.spaceMd
            spacing: Tokens.Theme.spaceSm
            Label { text: (i18n.revision, i18n.t("review.title")); color: Tokens.Theme.textPrimary; font.pixelSize: Tokens.Theme.textEmpty }
            RowLayout {
                Layout.fillWidth: true
                Label { text: (i18n.revision, i18n.t("review.rating")); color: Tokens.Theme.textSecondary }
                FilterComboBox {
                    id: rating
                    objectName: "personalRatingInput"
                    Layout.preferredWidth: 140
                    model: ["Puan yok", "1 / 10", "2 / 10", "3 / 10", "4 / 10", "5 / 10", "6 / 10", "7 / 10", "8 / 10", "9 / 10", "10 / 10"]
                    onActivated: editor.dirty = true
                }
                Label {
                    Layout.fillWidth: true
                    text: (i18n.revision, i18n.t("review.rating_help"))
                    color: Tokens.Theme.textMuted
                    wrapMode: Text.WordWrap
                }
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 92
                clip: true
                TextArea {
                    id: note
                    objectName: "personalNoteInput"
                    placeholderText: (i18n.revision, i18n.t("review.note_ph"))
                    color: Tokens.Theme.textPrimary
                    placeholderTextColor: Tokens.Theme.textMuted
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    onTextChanged: if (!editor.syncing) editor.dirty = true
                    background: Rectangle {
                        color: Tokens.Theme.surfaceElevated
                        radius: Tokens.Theme.radiusSm
                        border.color: note.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: note.text.length + " / 2000"
                    color: note.text.length > 2000 ? Tokens.Theme.danger : Tokens.Theme.textMuted
                }
                Item { Layout.fillWidth: true }
                IzlekButton {
                    objectName: "savePersonalReviewButton"
                    text: (i18n.revision, i18n.t("common.save"))
                    enabled: editor.matching && !editor.backend.busy && editor.mediaTitle.length > 0 && note.text.length <= 2000
                    onClicked: {
                        editor.backend.saveReview(editor.kind, editor.mediaId, rating.currentIndex, note.text)
                    }
                }
                IzlekButton {
                    objectName: "dismissMediaButton"
                    text: editor.matching && editor.backend.current.dismissed ? "Önerilerde yeniden göster" : "Bir daha önerme"
                    variant: "secondary"
                    enabled: editor.matching && !editor.backend.busy && editor.mediaTitle.length > 0
                    onClicked: editor.backend.setDismissed({mediaType: editor.kind, id: editor.mediaId, title: editor.mediaTitle}, !editor.backend.current.dismissed)
                }
            }
            Label {
                Layout.fillWidth: true
                visible: editor.matching && !!editor.backend.feedback
                text: editor.backend.feedback
                color: Tokens.Theme.textSecondary
                wrapMode: Text.WordWrap
            }
            Label {
                text: "Etiketler"
                color: Tokens.Theme.textPrimary
                font.pixelSize: Tokens.Theme.textEmpty
            }
            Label {
                Layout.fillWidth: true
                text: "Etiketler akıllı listelerde görünür; JSON yedeğe henüz dahil edilmez."
                color: Tokens.Theme.textMuted
                wrapMode: Text.WordWrap
            }
            Flow {
                objectName: "mediaTagsFlow"
                Layout.fillWidth: true
                spacing: Tokens.Theme.spaceXs
                Repeater {
                    model: tagsController.current
                    delegate: RowLayout {
                        required property var modelData
                        spacing: 2
                        Badge { text: modelData; tone: "accent" }
                        IzlekButton {
                            objectName: "removeMediaTagButton"
                            text: "×"
                            variant: "ghost"
                            Layout.preferredWidth: 28
                            enabled: !tagsController.busy && editor.mediaId > 0
                            Accessible.name: modelData + " etiketini kaldır"
                            onClicked: tagsController.removeTag(editor.kind, editor.mediaId, modelData)
                        }
                    }
                }
                Label {
                    visible: tagsController.current.length === 0
                    text: "Etiket yok"
                    color: Tokens.Theme.textMuted
                }
            }
            RowLayout {
                Layout.fillWidth: true
                FilterTextField {
                    id: tagInput
                    objectName: "mediaTagInput"
                    Layout.fillWidth: true
                    placeholderText: "Yeni etiket"
                    maximumLength: 80
                    enabled: editor.mediaId > 0 && !!editor.mediaTitle
                    onAccepted: editor.commitTag()
                }
                IzlekButton {
                    objectName: "addMediaTagButton"
                    text: "Ekle"
                    enabled: tagInput.text.trim().length > 0 && !tagsController.busy && editor.mediaId > 0
                    onClicked: editor.commitTag()
                }
            }
            Label {
                Layout.fillWidth: true
                visible: !!tagsController.feedback
                text: tagsController.feedback
                color: Tokens.Theme.textSecondary
                wrapMode: Text.WordWrap
            }
        }
    }
    function commitTag() {
        var name = tagInput.text.trim()
        if (!name.length || editor.mediaId <= 0) return
        tagsController.addTag(editor.kind, editor.mediaId, name)
        tagInput.text = ""
    }
}
