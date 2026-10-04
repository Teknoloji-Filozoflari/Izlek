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
        objectName: "movieDetailScroll"
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
                    IzlekButton {
                        objectName: "movieWatched"
                        text: "✓ İzlendi"
                        variant: page.controller.detail.status === "WATCHED" ? "primary" : "secondary"
                        enabled: !page.controller.saving
                        onClicked: page.controller.setStatus("WATCHED")
                    }
                    IzlekButton {
                        objectName: "movieUnwatched"
                        visible: !!page.controller.detail.status
                        text: "↺ İzlenmedi"
                        variant: "secondary"
                        enabled: !page.controller.saving
                        onClicked: page.controller.setStatus("PLANNED")
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
                    IzlekButton {
                        objectName: "removeMovieFromLibrary"
                        visible: !!page.controller.detail.status
                        enabled: !page.controller.saving
                        text: "Kütüphaneden Kaldır"
                        variant: "danger"
                        onClicked: page.controller.removeFromLibrary()
                    }
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
                    CastGrid {
                        objectName: "movieCastGrid"
                        Layout.fillWidth: true
                        cast: page.controller.detail.cast || []
                        photoObjectName: "movieActorPhoto"
                    }
                    Label {
                        visible: (page.controller.detail.cast || []).length === 0
                        text: "Oyuncu bilgisi bulunmuyor."
                        color: Tokens.Theme.textMuted
                    }
                    GridLayout {
                        objectName: "movieProductionInfo"
                        Layout.fillWidth: true
                        columns: width >= 850 ? 3 : 1
                        columnSpacing: Tokens.Theme.spaceLg
                        rowSpacing: Tokens.Theme.spaceMd
                        Repeater {
                            model: [
                                {title: "Yönetmen", values: page.controller.detail.directors || []},
                                {title: "Yapım Şirketleri", values: page.controller.detail.companies || []},
                                {title: "Yapım Ülkeleri", values: page.controller.detail.countries || []}
                            ]
                            ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.preferredWidth: 1
                                Layout.minimumWidth: 0
                                Layout.alignment: Qt.AlignTop
                                SectionHeader { title: modelData.title; Layout.fillWidth: true }
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.values.join(", ") || "Bilgi bulunmuyor."
                                    color: Tokens.Theme.textSecondary
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: width >= 850 ? 2 : 1
                        columnSpacing: Tokens.Theme.spaceLg
                        rowSpacing: Tokens.Theme.spaceMd
                        ProviderSection {
                            objectName: "movieProviders"
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            Layout.minimumWidth: 0
                            Layout.alignment: Qt.AlignTop
                            groups: page.providerGroups
                            providerLink: page.controller.detail.providerLink || ""
                            onProviderLinkRequested: page.controller.openProviderLink()
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            Layout.minimumWidth: 0
                            Layout.alignment: Qt.AlignTop
                            SectionHeader { title: "Fragman"; Layout.fillWidth: true }
                            IzlekButton {
                                text: "Fragmanı İzle"
                                enabled: !!page.controller.detail.trailerUrl
                                onClicked: page.controller.openTrailer()
                            }
                        }
                    }
                    ColumnLayout {
                        objectName: "movieRelatedGrid"
                        Layout.fillWidth: true
                        SectionHeader { title: "Önerilen Filmler"; Layout.fillWidth: true }
                        HorizontalMediaStrip {
                            objectName: "movieRelatedStrip"
                            Layout.fillWidth: true
                            visible: items.length > 0
                            items: page.controller.detail.recommendations || []
                            onMediaActivated: function(media) { page.movieSelected(media.id) }
                        }
                        Label {
                            visible: (page.controller.detail.recommendations || []).length === 0
                            text: "Önerilen film bulunmuyor."
                            color: Tokens.Theme.textMuted
                        }
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
