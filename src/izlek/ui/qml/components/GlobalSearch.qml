import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Popup {
    id: overlay
    property var controller
    signal resultActivated(string kind, int itemId)
    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Tokens.Theme.space2xl
    width: Math.min(680, parent.width - 2 * Tokens.Theme.spaceLg)
    height: Math.min(620, parent.height - 2 * Tokens.Theme.space2xl)
    modal: true
    focus: true
    padding: Tokens.Theme.spaceLg
    closePolicy: Popup.CloseOnEscape
    onOpened: searchInput.forceActiveFocus()
    onClosed: {
        debounce.stop()
        searchInput.text = ""
        controller.clear()
    }

    Timer {
        id: debounce
        interval: 300
        repeat: false
        onTriggered: overlay.controller.search(searchInput.text)
    }

    background: Rectangle {
        color: Tokens.Theme.surface
        radius: Tokens.Theme.radiusLg
        border.color: Tokens.Theme.border
    }

    contentItem: ColumnLayout {
        spacing: Tokens.Theme.spaceMd
        RowLayout {
            Layout.fillWidth: true
            Label {
                text: "Global Arama"
                color: Tokens.Theme.textPrimary
                font.pixelSize: Tokens.Theme.textHeading
                font.weight: Tokens.Theme.weightDemiBold
                Layout.fillWidth: true
            }
            IconButton {
                iconSource: Qt.resolvedUrl("../../../resources/icons/close.svg")
                toolTipText: "Kapat"
                onClicked: overlay.close()
            }
        }
        SearchField {
            id: searchInput
            objectName: "globalSearchInput"
            Layout.fillWidth: true
            Layout.preferredHeight: Tokens.Theme.controlHeight + 4
            onTextChanged: {
                debounce.stop()
                overlay.controller.clear()
                if (text.trim().length >= 3)
                    debounce.start()
            }
            Keys.onEscapePressed: function(event) {
                overlay.close()
                event.accepted = true
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label {
                text: "Arama türü"
                color: Tokens.Theme.textSecondary
            }
            ComboBox {
                objectName: "globalSearchMediaType"
                Layout.fillWidth: true
                model: ["Film ve Dizi", "Film", "Dizi"]
                currentIndex: ["all", "movie", "tv"].indexOf(overlay.controller.mediaType)
                Accessible.name: "Arama türü"
                onActivated: {
                    debounce.stop()
                    overlay.controller.setMediaType(["all", "movie", "tv"][currentIndex])
                    if (searchInput.text.trim().length >= 3)
                        debounce.start()
                }
            }
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: parent.width
                spacing: Tokens.Theme.spaceMd

                Label {
                    visible: searchInput.text.trim().length < 3
                    Layout.fillWidth: true
                    text: "Aramak için en az 3 karakter yazın."
                    color: Tokens.Theme.textSecondary
                }
                BusyIndicator {
                    visible: overlay.controller.busy
                    running: visible
                    Layout.alignment: Qt.AlignHCenter
                }
                EmptyState {
                    visible: searchInput.text.trim().length >= 3
                             && !overlay.controller.busy
                             && !overlay.controller.error
                             && overlay.controller.movies.length === 0
                             && overlay.controller.shows.length === 0
                    Layout.fillWidth: true
                    title: "Sonuç bulunamadı"
                    description: "Başka bir adla tekrar arayın."
                }
                EmptyState {
                    visible: !!overlay.controller.error
                             && !overlay.controller.busy
                    Layout.fillWidth: true
                    title: "Arama tamamlanamadı"
                    description: overlay.controller.error
                    actionText: "Tekrar Dene"
                    onActionRequested: overlay.controller.search(searchInput.text)
                }
                Label {
                    visible: overlay.controller.movies.length > 0
                    text: "Filmler"
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textEmpty
                    font.weight: Tokens.Theme.weightDemiBold
                }
                Repeater {
                    model: overlay.controller.movies
                    SearchResultCard {
                        objectName: "movieSearchResult"
                        Layout.fillWidth: true
                        media: modelData
                        onActivated: function(kind, itemId) {
                            overlay.resultActivated(kind, itemId)
                        }
                    }
                }
                Label {
                    visible: overlay.controller.shows.length > 0
                    text: "Diziler"
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textEmpty
                    font.weight: Tokens.Theme.weightDemiBold
                }
                Repeater {
                    model: overlay.controller.shows
                    SearchResultCard {
                        objectName: "tvSearchResult"
                        Layout.fillWidth: true
                        media: modelData
                        onActivated: function(kind, itemId) {
                            overlay.resultActivated(kind, itemId)
                        }
                    }
                }
            }
        }
    }
}
