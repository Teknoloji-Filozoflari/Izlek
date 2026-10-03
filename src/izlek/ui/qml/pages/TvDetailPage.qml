import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property var controller
    property string pageTitle: "Dizi Detayı"
    property string bulkScope: ""
    property bool bulkWatched: false
    readonly property var providerGroups: controller.detail.providers || ({})
    signal backRequested()
    signal tvSelected(int itemId)
    color: Tokens.Theme.background

    function confirmBulk(scope, watched) {
        bulkScope = scope
        bulkWatched = watched
        bulkDialog.title = scope === "season" ? "Sezonu güncelle" : "Diziyi güncelle"
        bulkDialog.message = (scope === "season" ? "Sezonun" : "Dizinin")
                + " bütün bölümleri " + (watched ? "izlendi" : "izlenmedi")
                + " olarak işaretlensin mi?"
        bulkDialog.open()
    }

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
                title: "Dizi yüklenemedi"
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
                    Rectangle { anchors.fill: parent; color: Tokens.Theme.scrim }
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
                                text: (page.controller.detail.firstAirDate || "Tarih bilinmiyor")
                                      + (page.controller.detail.lastAirDate
                                         ? " – " + page.controller.detail.lastAirDate : "")
                                color: Tokens.Theme.textPrimary
                            }
                            Label {
                                text: page.controller.detail.seriesStatus || ""
                                color: Tokens.Theme.textSecondary
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
                            }
                            Label {
                                objectName: "tvTmdbSourceLabel"
                                text: "Dizi bilgileri ve görseller TMDB tarafından sağlanır"
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
                        objectName: "addTvToLibrary"
                        visible: !page.controller.detail.status
                        enabled: !page.controller.saving
                        text: "Kütüphaneye Ekle"
                        onClicked: page.controller.setStatus("PLANNED")
                    }
                    StatusSelector {
                        objectName: "tvStatusSelector"
                        status: page.controller.detail.status || ""
                        enabled: !page.controller.saving
                        onStatusSelected: function(status) { page.controller.setStatus(status) }
                    }
                    FavoriteButton {
                        objectName: "tvFavorite"
                        checked: !!page.controller.detail.favorite
                        enabled: !page.controller.saving
                        onToggledFavorite: function(favorite) {
                            page.controller.setFavorite(favorite)
                        }
                    }
                    IzlekButton {
                        objectName: "tvListOpen"
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
                Label {
                    objectName: "newEpisodesNotice"
                    visible: !!page.controller.detail.newUnwatchedEpisodes
                    Layout.leftMargin: Tokens.Theme.spaceXl
                    Layout.rightMargin: Tokens.Theme.spaceXl
                    Layout.fillWidth: true
                    text: page.controller.detail.unwatchedAiredCount
                          + " yayınlanmış izlenmemiş bölüm var. Takip durumun korunuyor."
                    color: Tokens.Theme.accent
                    wrapMode: Text.WordWrap
                }
                Label {
                    visible: page.controller.detail.status === "WATCHED"
                             && page.controller.detail.missingEpisodeMetadataCount > 0
                    Layout.leftMargin: Tokens.Theme.spaceXl
                    Layout.rightMargin: Tokens.Theme.spaceXl
                    Layout.fillWidth: true
                    text: "Yeni bölüm bilgisi var. Ayrıntı için sezonu açın."
                    color: Tokens.Theme.textSecondary
                    wrapMode: Text.WordWrap
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
                    SectionHeader { title: "Sezonlar ve Bölümler"; Layout.fillWidth: true }
                    ComboBox {
                        id: seasonSelector
                        objectName: "tvSeasonSelector"
                        Layout.preferredWidth: 280
                        model: page.controller.detail.seasons || []
                        textRole: "name"
                        currentIndex: {
                            var entries = page.controller.detail.seasons || []
                            for (var i = 0; i < entries.length; i++)
                                if (entries[i].number === page.controller.selectedSeason)
                                    return i
                            return -1
                        }
                        onActivated: function(index) {
                            page.controller.selectSeason(model[index].number)
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Tokens.Theme.spaceSm
                        IzlekButton {
                            objectName: "seasonWatched"
                            text: "Sezonu İzlendi Yap"
                            enabled: !page.controller.saving && !page.controller.seasonBusy
                            onClicked: page.confirmBulk("season", true)
                        }
                        IzlekButton {
                            objectName: "seasonUnwatched"
                            text: "Sezonu İzlenmedi Yap"
                            variant: "secondary"
                            enabled: !page.controller.saving && !page.controller.seasonBusy
                            onClicked: page.confirmBulk("season", false)
                        }
                        Item { Layout.fillWidth: true }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Tokens.Theme.spaceSm
                        IzlekButton {
                            objectName: "seriesWatched"
                            text: "Diziyi İzlendi Yap"
                            enabled: !page.controller.saving && !page.controller.seasonBusy
                            onClicked: page.confirmBulk("series", true)
                        }
                        IzlekButton {
                            objectName: "seriesUnwatched"
                            text: "Diziyi İzlenmedi Yap"
                            variant: "secondary"
                            enabled: !page.controller.saving && !page.controller.seasonBusy
                            onClicked: page.confirmBulk("series", false)
                        }
                        Item { Layout.fillWidth: true }
                    }
                    BusyIndicator {
                        visible: page.controller.seasonBusy
                        running: visible
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Label {
                        visible: !!page.controller.seasonError
                        text: page.controller.seasonError
                        color: Tokens.Theme.textSecondary
                    }
                    ListView {
                        id: episodesList
                        objectName: "episodesList"
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(contentHeight, 520)
                        model: page.controller.episodes
                        spacing: Tokens.Theme.spaceSm
                        clip: true
                        reuseItems: true
                        boundsBehavior: Flickable.StopAtBounds
                        delegate: Rectangle {
                            required property var modelData
                            width: episodesList.width
                            height: Math.max(130, episodeText.implicitHeight + 32)
                            radius: Tokens.Theme.radiusMd
                            color: Tokens.Theme.surface
                            border.color: Tokens.Theme.border
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: Tokens.Theme.spaceMd
                                spacing: Tokens.Theme.spaceMd
                                Image {
                                    Layout.preferredWidth: 160
                                    Layout.preferredHeight: 90
                                    source: modelData.still || ""
                                    asynchronous: true
                                    fillMode: Image.PreserveAspectCrop
                                    sourceSize.width: Math.round(160 * Screen.devicePixelRatio)
                                    sourceSize.height: Math.round(90 * Screen.devicePixelRatio)
                                }
                                ColumnLayout {
                                    id: episodeText
                                    Layout.fillWidth: true
                                    Label {
                                        Layout.fillWidth: true
                                        text: modelData.number + ". " + modelData.name
                                        color: Tokens.Theme.textPrimary
                                        font.weight: Tokens.Theme.weightDemiBold
                                        wrapMode: Text.WordWrap
                                    }
                                    Label {
                                        text: modelData.date || "Tarih bilinmiyor"
                                        color: Tokens.Theme.textMuted
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text: modelData.overview || "Açıklama bulunmuyor."
                                        color: Tokens.Theme.textSecondary
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 3
                                        elide: Text.ElideRight
                                    }
                                }
                                CheckBox {
                                    objectName: "episodeWatched"
                                    text: "İzlendi"
                                    checked: !!modelData.watched
                                    enabled: !page.controller.saving
                                    onClicked: page.controller.setEpisodeWatched(
                                                   modelData.number, checked)
                                }
                            }
                        }
                        ScrollBar.vertical: ScrollBar {
                            policy: episodesList.contentHeight > episodesList.height
                                    ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                        }
                    }
                    Label {
                        visible: !page.controller.seasonBusy
                                 && page.controller.episodes.length === 0
                                 && !page.controller.seasonError
                        text: "Bu sezonda bölüm bulunmuyor."
                        color: Tokens.Theme.textMuted
                    }
                    SectionHeader { title: "Oyuncular"; Layout.fillWidth: true }
                    Repeater {
                        model: page.controller.detail.cast || []
                        Label {
                            text: modelData.name + (modelData.character
                                  ? " — " + modelData.character : "")
                            color: Tokens.Theme.textSecondary
                        }
                    }
                    SectionHeader { title: "Yaratıcılar"; Layout.fillWidth: true }
                    Label {
                        text: (page.controller.detail.creators || []).join(", ")
                              || "Bilgi bulunmuyor."
                        color: Tokens.Theme.textSecondary
                    }
                    SectionHeader { title: "Yapım Şirketleri"; Layout.fillWidth: true }
                    Label {
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
                        objectName: "tvProviders"
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
                    SectionHeader { title: "Benzer"; Layout.fillWidth: true }
                    Repeater {
                        model: page.controller.detail.similar || []
                        SearchResultCard {
                            Layout.fillWidth: true
                            media: modelData
                            onActivated: function(kind, itemId) { page.tvSelected(itemId) }
                        }
                    }
                    SectionHeader { title: "Öneriler"; Layout.fillWidth: true }
                    Repeater {
                        model: page.controller.detail.recommendations || []
                        SearchResultCard {
                            Layout.fillWidth: true
                            media: modelData
                            onActivated: function(kind, itemId) { page.tvSelected(itemId) }
                        }
                    }
                }
            }
            Item { Layout.preferredHeight: Tokens.Theme.spaceXl }
        }
    }

    IzlekDialog {
        id: bulkDialog
        objectName: "tvBulkDialog"
        parent: Overlay.overlay
        confirmText: "Uygula"
        onConfirmed: {
            if (page.bulkScope === "season")
                page.controller.setSeasonWatched(page.bulkWatched)
            else
                page.controller.setSeriesWatched(page.bulkWatched)
        }
    }
    Dialog {
        id: listDialog
        objectName: "tvListDialog"
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
                objectName: "tvListName"
                Layout.fillWidth: true
                placeholderText: "Liste adı"
                color: Tokens.Theme.textPrimary
                maximumLength: 200
                onAccepted: {
                    if (text.trim().length > 0) {
                        page.controller.addToList(text)
                        listDialog.close()
                    }
                }
            }
            Label {
                visible: (page.controller.detail.availableLists || []).length > 0
                Layout.fillWidth: true
                text: "Listeler: "
                      + (page.controller.detail.availableLists || []).join(", ")
                color: Tokens.Theme.textMuted
                wrapMode: Text.WordWrap
            }
            IzlekButton {
                objectName: "tvListAdd"
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
