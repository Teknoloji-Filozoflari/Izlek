import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property var controller
    readonly property string pageKind: "movie"
    property string pageTitle: (i18n.revision, i18n.t("page.movie_detail"))
    property int mediaId: 0
    readonly property bool filterPopupOpen: personalReview.filterPopupOpen
    readonly property var providerGroups: controller.detail.providers || ({})
    signal backRequested()
    signal movieSelected(int itemId)
    signal actorSelected(int personId, string name)
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
                text: (i18n.revision, i18n.t("common.back"))
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
                title: (i18n.revision, i18n.t("detail.movie_load_failed"))
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
                                objectName: "movieImdbRating"
                                visible: !!(page.controller.detail.imdbRating)
                                text: "IMDb: " + (page.controller.detail.imdbRating || "")
                                      + (page.controller.detail.imdbVotes
                                         ? " (" + page.controller.detail.imdbVotes + ")" : "")
                                color: Tokens.Theme.textSecondary
                                font.pixelSize: Tokens.Theme.textBody
                            }
                            Label {
                                objectName: "movieTraktRating"
                                visible: page.controller.detail.traktRating !== undefined
                                         && page.controller.detail.traktRating !== null
                                         && page.controller.detail.traktRating !== ""
                                text: "Trakt: " + (page.controller.detail.traktRating || 0)
                                      + (page.controller.detail.traktVotes
                                         ? " (" + page.controller.detail.traktVotes + ")" : "")
                                color: Tokens.Theme.textSecondary
                                font.pixelSize: Tokens.Theme.textBody
                            }
                            Label {
                                objectName: "movieTmdbSourceLabel"
                                text: (i18n.revision, i18n.t("detail.movie_attribution"))
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
                        text: (i18n.revision, i18n.t("detail.add_library"))
                        onClicked: page.controller.setStatus("PLANNED")
                    }
                    IzlekButton {
                        objectName: "movieWatched"
                        text: page.controller.detail.status === "WATCHED"
                              ? "Yeniden izledim"
                              : (i18n.revision, i18n.t("status.mark_watched"))
                        variant: page.controller.detail.status === "WATCHED" ? "primary" : "secondary"
                        enabled: !page.controller.saving
                        onClicked: page.controller.setStatus("WATCHED")
                    }
                    IzlekButton {
                        objectName: "movieUnwatched"
                        visible: !!page.controller.detail.status
                        text: (i18n.revision, i18n.t("status.mark_unwatched"))
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
                        text: (i18n.revision, i18n.t("detail.add_list"))
                        variant: "secondary"
                        enabled: !page.controller.saving
                        onClicked: listDialog.open()
                    }
                    IzlekButton {
                        objectName: "movieCollectionToList"
                        visible: (page.controller.detail.collectionId || 0) > 0
                        text: (i18n.revision, i18n.t("detail.add_collection_list"))
                        variant: "secondary"
                        enabled: !page.controller.saving
                        Accessible.name: page.controller.detail.collectionName
                            ? ((i18n.revision, i18n.t("detail.add_collection_list"))
                               + " — " + page.controller.detail.collectionName)
                            : (i18n.revision, i18n.t("detail.add_collection_list"))
                        onClicked: page.controller.addCollectionToList()
                    }
                    IzlekButton {
                        objectName: "togglePersonalReviewButton"
                        text: personalReview.expanded ? "Puan ve notu kapat" : "Puan ve not"
                        variant: "secondary"
                        enabled: page.mediaId > 0 && !!page.controller.detail.title
                        onClicked: personalReview.expanded = !personalReview.expanded
                    }
                    Item { Layout.fillWidth: true }
                    IzlekButton {
                        objectName: "removeMovieFromLibrary"
                        visible: !!page.controller.detail.status
                        enabled: !page.controller.saving
                        text: (i18n.revision, i18n.t("detail.remove_library"))
                        variant: "danger"
                        onClicked: page.controller.removeFromLibrary()
                    }
                }
                Label {
                    objectName: "movieRewatchCount"
                    visible: (page.controller.detail.rewatchCount || 0) > 0
                    Layout.leftMargin: Tokens.Theme.spaceXl
                    text: (page.controller.detail.rewatchCount || 0) + " kez yeniden izlendi"
                    color: Tokens.Theme.textSecondary
                    font.pixelSize: Tokens.Theme.textSmall
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

                    PersonalReview {
                        id: personalReview
                        objectName: "moviePersonalReview"
                        Layout.fillWidth: true
                        kind: "movie"
                        mediaId: page.mediaId
                        mediaTitle: page.controller.detail.title || ""
                    }
                    SectionHeader { title: (i18n.revision, i18n.t("detail.overview")); Layout.fillWidth: true }
                    Label {
                        Layout.fillWidth: true
                        text: page.controller.detail.overview || "Açıklama bulunmuyor."
                        color: Tokens.Theme.textSecondary
                        wrapMode: Text.WordWrap
                    }
                    SectionHeader { title: (i18n.revision, i18n.t("detail.cast")); Layout.fillWidth: true }
                    CastGrid {
                        objectName: "movieCastGrid"
                        Layout.fillWidth: true
                        cast: page.controller.detail.cast || []
                        photoObjectName: "movieActorPhoto"
                        onActorActivated: function(personId, name) { page.actorSelected(personId, name) }
                    }
                    Label {
                        visible: (page.controller.detail.cast || []).length === 0
                        text: (i18n.revision, i18n.t("detail.cast_empty"))
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
                                {title: (i18n.revision, i18n.t("detail.director")), values: page.controller.detail.directors || []},
                                {title: (i18n.revision, i18n.t("detail.companies")), values: page.controller.detail.companies || []},
                                {title: (i18n.revision, i18n.t("detail.countries")), values: page.controller.detail.countries || []}
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
                            SectionHeader { title: (i18n.revision, i18n.t("detail.trailer")); Layout.fillWidth: true }
                            IzlekButton {
                                text: (i18n.revision, i18n.t("detail.watch_trailer"))
                                enabled: !!page.controller.detail.trailerUrl
                                onClicked: page.controller.openTrailer()
                            }
                        }
                    }
                    ColumnLayout {
                        objectName: "movieRelatedGrid"
                        Layout.fillWidth: true
                        SectionHeader { title: (i18n.revision, i18n.t("detail.similar_movies")); Layout.fillWidth: true }
                        HorizontalMediaStrip {
                            objectName: "movieRelatedStrip"
                            Layout.fillWidth: true
                            visible: items.length > 0
                            items: page.controller.detail.recommendations || []
                            onMediaActivated: function(media) { page.movieSelected(media.id) }
                        }
                        Label {
                            visible: (page.controller.detail.recommendations || []).length === 0
                            text: (i18n.revision, i18n.t("detail.similar_movies_empty"))
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
        title: (i18n.revision, i18n.t("lists.add_to_list"))
        width: Math.min(420, page.width - 2 * Tokens.Theme.spaceLg)
        x: (page.width - width) / 2
        y: (page.height - height) / 2
        closePolicy: Popup.CloseOnEscape
        onOpened: listName.forceActiveFocus()
        contentItem: ColumnLayout {
            spacing: Tokens.Theme.spaceMd
            Label {
                Layout.fillWidth: true
                text: (i18n.revision, i18n.t("lists.add_hint"))
                color: Tokens.Theme.textSecondary
                wrapMode: Text.WordWrap
            }
            TextField {
                id: listName
                objectName: "movieListName"
                Layout.fillWidth: true
                placeholderText: (i18n.revision, i18n.t("lists.name_ph"))
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
                text: (i18n.revision, i18n.t("common.add"))
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
