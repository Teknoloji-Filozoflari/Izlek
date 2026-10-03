import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property var controller
    property string pageTitle: "Film Detayı"
    readonly property var providerGroups: controller.detail.providers || ({})
    signal backRequested()
    signal movieSelected(int itemId)
    color: Tokens.Theme.background

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Tokens.Theme.spaceLg

            IzlekButton {
                Layout.leftMargin: Tokens.Theme.spaceXl
                Layout.topMargin: Tokens.Theme.spaceLg
                text: "← Geri"
                variant: "secondary"
                onClicked: page.backRequested()
            }
            BusyIndicator {
                visible: page.controller.busy
                running: visible
                Layout.alignment: Qt.AlignHCenter
            }
            EmptyState {
                visible: !!page.controller.error
                Layout.fillWidth: true
                title: "Film yüklenemedi"
                description: page.controller.error
            }
            ColumnLayout {
                visible: !!page.controller.detail.title
                Layout.fillWidth: true
                spacing: Tokens.Theme.spaceLg

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 300
                    clip: true
                    Image {
                        anchors.fill: parent
                        source: page.controller.detail.backdrop || ""
                        asynchronous: true
                        fillMode: Image.PreserveAspectCrop
                        sourceSize.width: Math.round(width * Screen.devicePixelRatio)
                        sourceSize.height: Math.round(height * Screen.devicePixelRatio)
                    }
                    Rectangle {
                        anchors.fill: parent
                        color: Tokens.Theme.scrim
                    }
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: Tokens.Theme.spaceXl
                        spacing: Tokens.Theme.spaceXl
                        Image {
                            Layout.preferredWidth: 160
                            Layout.preferredHeight: 240
                            source: page.controller.detail.poster || ""
                            asynchronous: true
                            fillMode: Image.PreserveAspectFit
                            sourceSize.width: Math.round(160 * Screen.devicePixelRatio)
                            sourceSize.height: Math.round(240 * Screen.devicePixelRatio)
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Tokens.Theme.spaceSm
                            Label {
                                Layout.fillWidth: true
                                text: page.controller.detail.title || ""
                                color: Tokens.Theme.textPrimary
                                font.pixelSize: Tokens.Theme.textHeading
                                font.weight: Tokens.Theme.weightDemiBold
                                wrapMode: Text.WordWrap
                            }
                            Label {
                                text: (page.controller.detail.year || "Yıl bilinmiyor")
                                      + " · " + (page.controller.detail.runtime
                                                ? page.controller.detail.runtime + " dk" : "Süre yok")
                                color: Tokens.Theme.textPrimary
                                font.pixelSize: Tokens.Theme.textBody
                            }
                            Label {
                                Layout.fillWidth: true
                                text: (page.controller.detail.genres || []).join(" · ")
                                color: Tokens.Theme.textSecondary
                                wrapMode: Text.WordWrap
                            }
                            Label {
                                text: "TMDb: " + (page.controller.detail.score || 0).toFixed(1) + " / 10"
                                color: Tokens.Theme.accent
                                font.pixelSize: Tokens.Theme.textBody
                            }
                            Label {
                                objectName: "movieTmdbSourceLabel"
                                text: "Film bilgileri ve görseller TMDB tarafından sağlanır"
                                color: Tokens.Theme.textSecondary
                                font.pixelSize: Tokens.Theme.textSmall
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: Tokens.Theme.spaceXl
                    Layout.rightMargin: Tokens.Theme.spaceXl
                    spacing: Tokens.Theme.spaceMd
                    IzlekButton {
                        objectName: "addMovieToLibrary"
                        visible: !page.controller.detail.status
                        enabled: !page.controller.saving
                        text: "Kütüphaneye Ekle"
                        onClicked: page.controller.setStatus("PLANNED")
                    }
                    StatusSelector {
                        objectName: "movieStatusSelector"
                        status: page.controller.detail.status || ""
                        enabled: !page.controller.saving
                        onStatusSelected: function(status) {
                            page.controller.setStatus(status)
                        }
                    }
                    FavoriteButton {
                        objectName: "movieFavorite"
                        checked: !!page.controller.detail.favorite
                        enabled: !page.controller.saving
                        onToggledFavorite: function(favorite) {
                            page.controller.setFavorite(favorite)
                        }
                    }
                    IzlekButton {
                        objectName: "movieListOpen"
                        text: "Listeye Ekle"
                        variant: "secondary"
                        enabled: !page.controller.saving
                        onClicked: listDialog.open()
                    }
                    Item { Layout.fillWidth: true }
                }
                Label {
                    visible: page.controller.feedback.length > 0
                    Layout.leftMargin: Tokens.Theme.spaceXl
                    text: page.controller.feedback
                    color: Tokens.Theme.accent
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: Tokens.Theme.spaceXl
                    Layout.rightMargin: Tokens.Theme.spaceXl
                    spacing: Tokens.Theme.spaceLg

                    SectionHeader { title: "Açıklama"; Layout.fillWidth: true }
                    Label {
                        Layout.fillWidth: true
                        text: page.controller.detail.overview || "Açıklama bulunmuyor."
                        color: Tokens.Theme.textSecondary
                        wrapMode: Text.WordWrap
                    }
                    SectionHeader { title: "Oyuncular"; Layout.fillWidth: true }
                    Repeater {
                        model: page.controller.detail.cast || []
                        Label {
                            Layout.fillWidth: true
                            text: modelData.name + (modelData.character
                                  ? " — " + modelData.character : "")
                            color: Tokens.Theme.textSecondary
                        }
                    }
                    Label {
                        visible: !page.controller.detail.cast
                                 || page.controller.detail.cast.length === 0
                        text: "Oyuncu bilgisi bulunmuyor."
                        color: Tokens.Theme.textMuted
                    }
                    SectionHeader { title: "Yönetmen"; Layout.fillWidth: true }
                    Label {
                        text: (page.controller.detail.directors || []).join(", ")
                              || "Bilgi bulunmuyor."
                        color: Tokens.Theme.textSecondary
                    }
                    SectionHeader { title: "Yapım Şirketleri"; Layout.fillWidth: true }
                    Label {
                        Layout.fillWidth: true
                        text: (page.controller.detail.companies || []).join(", ")
                              || "Bilgi bulunmuyor."
                        color: Tokens.Theme.textSecondary
                        wrapMode: Text.WordWrap
                    }
                    SectionHeader { title: "Yapım Ülkeleri"; Layout.fillWidth: true }
                    Label {
                        text: (page.controller.detail.countries || []).join(", ")
                              || "Bilgi bulunmuyor."
                        color: Tokens.Theme.textSecondary
                    }
                    ProviderSection {
                        objectName: "movieProviders"
                        Layout.fillWidth: true
                        groups: page.providerGroups
                        providerLink: page.controller.detail.providerLink || ""
                        onProviderLinkRequested: page.controller.openProviderLink()
                    }
                    SectionHeader { title: "Fragman"; Layout.fillWidth: true }
                    IzlekButton {
                        text: "Fragmanı İzle"
                        enabled: !!page.controller.detail.trailerUrl
                        onClicked: page.controller.openTrailer()
                    }
                    Label {
                        visible: !page.controller.detail.trailerUrl
                        text: "Fragman bulunmuyor."
                        color: Tokens.Theme.textMuted
                    }
                    SectionHeader { title: "Benzer"; Layout.fillWidth: true }
                    Repeater {
                        model: page.controller.detail.similar || []
                        SearchResultCard {
                            Layout.fillWidth: true
                            media: modelData
                            onActivated: function(kind, itemId) {
                                page.movieSelected(itemId)
                            }
                        }
                    }
                    Label {
                        visible: (page.controller.detail.similar || []).length === 0
                        text: "Benzer film bulunmuyor."
                        color: Tokens.Theme.textMuted
                    }
                    SectionHeader { title: "Öneriler"; Layout.fillWidth: true }
                    Repeater {
                        model: page.controller.detail.recommendations || []
                        SearchResultCard {
                            Layout.fillWidth: true
                            media: modelData
                            onActivated: function(kind, itemId) {
                                page.movieSelected(itemId)
                            }
                        }
                    }
                    Label {
                        visible: (page.controller.detail.recommendations || []).length === 0
                        text: "Öneri bulunmuyor."
                        color: Tokens.Theme.textMuted
                    }
                }
            }
            Item { Layout.preferredHeight: Tokens.Theme.spaceXl }
        }
    }

    Dialog {
        id: listDialog
        objectName: "movieListDialog"
        modal: true
        focus: true
        title: "Listeye Ekle"
        width: Math.min(420, page.width - 2 * Tokens.Theme.spaceLg)
        x: (page.width - width) / 2
        y: (page.height - height) / 2
        closePolicy: Popup.CloseOnEscape
        onOpened: listName.forceActiveFocus()
        contentItem: ColumnLayout {
            spacing: Tokens.Theme.spaceMd
            Label {
                Layout.fillWidth: true
                text: "Mevcut liste adını yazın veya yeni liste oluşturun."
                color: Tokens.Theme.textSecondary
                wrapMode: Text.WordWrap
            }
            TextField {
                id: listName
                objectName: "movieListName"
                Layout.fillWidth: true
                placeholderText: "Liste adı"
                color: Tokens.Theme.textPrimary
                onAccepted: {
                    if (text.trim().length > 0) {
                        page.controller.addToList(text)
                        listDialog.close()
                    }
                }
            }
            Label {
                visible: !!page.controller.detail.availableLists
                         && page.controller.detail.availableLists.length > 0
                Layout.fillWidth: true
                text: "Listeler: " + (page.controller.detail.availableLists || []).join(", ")
                color: Tokens.Theme.textMuted
                wrapMode: Text.WordWrap
            }
            IzlekButton {
                objectName: "movieListAdd"
                text: "Ekle"
                enabled: listName.text.trim().length > 0
                onClicked: {
                    page.controller.addToList(listName.text)
                    listDialog.close()
                }
            }
        }
        background: Rectangle {
            color: Tokens.Theme.surfaceElevated
            radius: Tokens.Theme.radiusMd
            border.color: Tokens.Theme.border
        }
    }
}
