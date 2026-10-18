import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property string kind: "movie"
    property string pageTitle: kind === "movie" ? "Filmler" : "Diziler"
    property var controller
    property var continueModelController: null
    property bool pageReady: false
    property bool selecting: false
    property bool filtersExpanded: false
    property var selectedIds: []
    property string feedback: ""
    readonly property bool filterPopupOpen: bulkDialog.visible || filterPanel.filterPopupOpen || sortBox.popup.visible
    readonly property string emptyTitle:
        kind === "tv" ? "Henüz dizi eklemedin" : "Henüz film eklemedin"
    readonly property string mediaNoun: kind === "movie" ? "film" : "dizi"
    signal mediaSelected(int tmdbId)
    color: Tokens.Theme.background

    function toggleSelection(itemId) {
        var next = selectedIds.slice()
        var index = next.indexOf(itemId)
        if (index >= 0) next.splice(index, 1)
        else next.push(itemId)
        selectedIds = next
    }
    Connections {
        target: page.controller
        function onItemsChanged() {
            var visibleIds = page.controller.items.map(function(item) { return item.tmdb_id })
            page.selectedIds = page.selectedIds.filter(function(id) { return visibleIds.indexOf(id) >= 0 })
        }
        function onBulkCompleted(count) {
            page.selectedIds = []
            page.selecting = false
            page.feedback = count + " içerik güncellendi."
        }
    }

    function refreshLibrary() {
        controller.refresh()
        if (kind === "tv" && continueModelController) continueModelController.refresh()
    }
    Component.onCompleted: {
        pageReady = true
        if (visible) refreshLibrary()
    }
    onVisibleChanged: {
        if (visible && pageReady) refreshLibrary()
    }
    Connections {
        target: page.continueModelController
        function onProgressSaved() { page.controller.refresh() }
    }

    ScrollView {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceLg
        contentWidth: availableWidth
        clip: true
    Column {
        width: parent.width
        spacing: Tokens.Theme.spaceSm

        RowLayout {
            width: parent.width
            height: 40
            Label {
                text: page.pageTitle
                color: Tokens.Theme.textPrimary
                font.pixelSize: Tokens.Theme.textHeading
                font.weight: Tokens.Theme.weightDemiBold
            }
            Item { Layout.fillWidth: true }
            IzlekButton {
                objectName: "toggleLibraryFiltersButton"
                text: page.filtersExpanded ? "Filtreleri kapat" : "Filtreler"
                variant: "secondary"
                onClicked: page.filtersExpanded = !page.filtersExpanded
            }
            IzlekButton {
                objectName: "toggleLibrarySelectionButton"
                text: page.selecting ? "Seçimi kapat" : "Seç"
                variant: "secondary"
                enabled: !page.controller.batchBusy
                onClicked: { page.selecting = !page.selecting; page.selectedIds = [] }
            }
            Label {
                text: (controller.stats.total || 0) + " " + page.mediaNoun
                color: Tokens.Theme.textSecondary
                font.pixelSize: Tokens.Theme.textBody
            }
        }

        LibraryFiltersPanel {
            id: filterPanel
            objectName: "libraryFiltersPanel"
            visible: page.filtersExpanded
            width: parent.width
            height: implicitHeight
            kind: page.kind
            controller: page.controller
            onApplied: page.selectedIds = []
        }
        Label {
            visible: page.controller.filtersActive
            width: parent.width
            text: controller.items.length + " eşleşme · Sürükleyerek sıralamak için filtreleri temizle."
            color: Tokens.Theme.textMuted
            wrapMode: Text.WordWrap
        }
        RowLayout {
            visible: page.selecting
            width: parent.width
            height: Tokens.Theme.controlHeight
            Label { text: page.selectedIds.length + " seçili"; color: Tokens.Theme.textPrimary }
            IzlekButton {
                objectName: "selectVisibleLibraryButton"
                text: "Görünenlerin tümü"
                variant: "secondary"
                enabled: !page.controller.batchBusy
                onClicked: page.selectedIds = page.controller.items.map(function(item) { return item.tmdb_id })
            }
            IzlekButton { text: "Temizle"; variant: "ghost"; enabled: !page.controller.batchBusy; onClicked: page.selectedIds = [] }
            Item { Layout.fillWidth: true }
            IzlekButton {
                objectName: "openLibraryBatchButton"
                text: "Toplu işlem"
                enabled: page.selectedIds.length > 0 && !page.controller.busy && !page.controller.batchBusy
                onClicked: { bulkDialog.selectedIds = page.selectedIds.slice(); bulkDialog.open() }
            }
        }
        Label {
            visible: !!page.feedback || !!page.controller.error
            width: parent.width
            text: page.controller.error || page.feedback
            color: page.controller.error ? Tokens.Theme.danger : Tokens.Theme.success
            wrapMode: Text.WordWrap
        }

        RowLayout {
            width: parent.width
            height: Tokens.Theme.controlHeight
            spacing: Tokens.Theme.spaceMd
            SegmentedControl {
                id: statusTabs
                visible: false
                objectName: page.kind === "movie" ? "movieStatusTabs" : "tvStatusTabs"
                options: ["İzlenecek", "İzleniyor", "İzlendi"]
                currentIndex: ["PLANNED", "WATCHING", "WATCHED"].indexOf(controller.status)
                onSelected: function(index) {
                    controller.setStatus(["PLANNED", "WATCHING", "WATCHED"][index])
                }
            }
            SegmentedControl {
                objectName: page.kind === "movie" ? "movieCardDensity" : "tvCardDensity"
                options: ["Rahat", "Sıkı"]
                currentIndex: movieGrid.compact ? 1 : 0
                onSelected: function(index) { movieGrid.compact = index === 1 }
            }
            Item { Layout.fillWidth: true }
            Label {
                text: "Sırala"
                color: Tokens.Theme.textSecondary
            }
            ComboBox {
                id: sortBox
                objectName: page.kind === "movie" ? "movieSort" : "tvSort"
                Layout.preferredWidth: 168
                Layout.preferredHeight: Tokens.Theme.controlHeight
                model: [
                    { text: "Özel Sıram", value: "custom" },
                    { text: "Son Eklenen", value: "recent" },
                    { text: "Başlık", value: "title" },
                    { text: "Yıl", value: "year" },
                    { text: "TMDb Puanı", value: "score" }
                ]
                textRole: "text"
                valueRole: "value"
                currentIndex: ["custom", "recent", "title", "year", "score"].indexOf(controller.sortBy)
                onActivated: controller.setSort(currentValue)
                contentItem: Label {
                    text: sortBox.displayText
                    color: Tokens.Theme.textPrimary
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: Tokens.Theme.spaceSm
                }
                background: Rectangle {
                    color: Tokens.Theme.surface
                    radius: Tokens.Theme.radiusSm
                    border.color: sortBox.activeFocus ? Tokens.Theme.accent
                                                      : Tokens.Theme.border
                    border.width: sortBox.activeFocus ? 2 : 1
                }
                delegate: ItemDelegate {
                    width: sortBox.width
                    text: modelData.text
                    contentItem: Label {
                        text: parent.text
                        color: Tokens.Theme.textPrimary
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: parent.hovered ? Tokens.Theme.hoverSurface
                                              : Tokens.Theme.surfaceElevated
                    }
                }
                popup: Popup {
                    y: sortBox.height
                    width: sortBox.width
                    padding: 0
                    contentItem: ListView {
                        implicitHeight: contentHeight
                        model: sortBox.popup.visible ? sortBox.delegateModel : null
                    }
                    background: Rectangle {
                        color: Tokens.Theme.surfaceElevated
                        border.color: Tokens.Theme.border
                        radius: Tokens.Theme.radiusSm
                    }
                }
            }
        }

        Rectangle {
            objectName: "libraryGridFrame"
            width: parent.width
            clip: true
            readonly property int rowCount: Math.max(
                1, Math.ceil(controller.items.length / Math.max(1, movieGrid.columns)))
            height: Math.min(
                rowCount * movieGrid.cellHeight + 2 * Tokens.Theme.spaceSm,
                Math.max(160, page.height - 310))
            color: Tokens.Theme.surface
            radius: Tokens.Theme.radiusLg
            border.color: Tokens.Theme.border

            LibraryPosterGrid {
                id: movieGrid
                objectName: page.kind === "movie" ? "movieLibraryGrid"
                                                 : "tvLibraryGrid"
                anchors.fill: parent
                anchors.margins: Tokens.Theme.spaceSm
                visible: controller.items.length > 0
                items: controller.items
                controller: page.controller
                selectionMode: page.selecting
                selectedIds: page.selectedIds
                onSelectionToggled: function(itemId) { page.toggleSelection(itemId) }
                onPosterRequested: function(tmdbId) { controller.requestPoster(tmdbId) }
                onMediaActivated: function(tmdbId) { page.mediaSelected(tmdbId) }
                onFavoriteToggled: function(tmdbId, favorite) {
                    controller.setFavorite(tmdbId, favorite)
                }
                onReorderRequested: function(sourceId, targetId) {
                    controller.reorderMedia(sourceId, targetId)
                }
            }
            LoadingState {
                objectName: "libraryLoadingState"
                anchors.centerIn: parent
                width: parent.width - 2 * Tokens.Theme.spaceMd
                visible: controller.busy && controller.items.length === 0
                count: Math.max(2, Math.floor(width / (Tokens.Theme.cardWidth
                                                       + Tokens.Theme.gridGap)))
                skeletonPosterHeight: 210
            }
            EmptyState {
                objectName: page.kind === "movie" ? "movieLibraryEmpty"
                                                 : "tvLibraryEmpty"
                anchors.centerIn: parent
                width: parent.width - 2 * Tokens.Theme.spaceMd
                height: Math.min(206, parent.height)
                visible: !controller.busy && controller.items.length === 0
                title: controller.error || (controller.filtersActive ? "Filtreyle eşleşen içerik yok" : page.emptyTitle)
                description: controller.error ? "Lütfen tekrar deneyin."
                    : controller.filtersActive ? "Filtreleri genişletip yeniden deneyebilirsin."
                    : (page.kind === "movie" ? "Film" : "Dizi")
                      + " arayıp kütüphanene eklediğinde burada görünecek."
            }
        }

        ColumnLayout {
            width: parent.width
            height: 142
            spacing: Tokens.Theme.spaceXs
            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: page.kind === "movie" ? "Favori Filmler" : "Favori Diziler"
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textEmpty
                    font.weight: Tokens.Theme.weightDemiBold
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: controller.favorites.length + " " + page.mediaNoun
                    color: Tokens.Theme.textMuted
                }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Tokens.Theme.surface
                radius: Tokens.Theme.radiusMd
                border.color: Tokens.Theme.border
                Label {
                    anchors.centerIn: parent
                    visible: controller.favorites.length === 0
                    text: "Favori " + page.mediaNoun + " yok"
                    color: Tokens.Theme.textSecondary
                }
                ListView {
                    id: favoritesStrip
                    objectName: page.kind === "movie" ? "favoriteMoviesStrip"
                                                     : "favoriteShowsStrip"
                    anchors.fill: parent
                    anchors.margins: Tokens.Theme.spaceXs
                    orientation: ListView.Horizontal
                    spacing: Tokens.Theme.spaceSm
                    clip: true
                    model: controller.favorites
                    delegate: ItemDelegate {
                        id: favoriteCard
                        required property var modelData
                        property string resolvedPoster: modelData.poster || ""
                        Connections {
                            target: page.controller
                            function onPosterAvailable(tmdbId, url) {
                                if (tmdbId === favoriteCard.modelData.tmdb_id)
                                    favoriteCard.resolvedPoster = url
                            }
                        }
                        width: 198
                        height: favoritesStrip.height
                        Component.onCompleted: Qt.callLater(function() {
                            controller.requestPoster(modelData.tmdb_id)
                        })
                        onClicked: page.mediaSelected(modelData.tmdb_id)
                        background: Rectangle {
                            color: parent.hovered ? Tokens.Theme.hoverSurface
                                                  : Tokens.Theme.surfaceElevated
                            radius: Tokens.Theme.radiusSm
                        }
                        contentItem: RowLayout {
                            spacing: Tokens.Theme.spaceSm
                            Image {
                                Layout.preferredWidth: 57
                                Layout.fillHeight: true
                                source: favoriteCard.resolvedPoster
                                fillMode: Image.PreserveAspectCrop
                                sourceSize.width: Math.round(57 * Screen.devicePixelRatio)
                                sourceSize.height: Math.round(height * Screen.devicePixelRatio)
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.title || ""
                                    color: Tokens.Theme.textPrimary
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                                Label {
                                    text: modelData.year || ""
                                    color: Tokens.Theme.textMuted
                                    font.pixelSize: Tokens.Theme.textSmall
                                }
                            }
                            FavoriteButton {
                                Layout.preferredWidth: Tokens.Theme.controlHeight
                                checked: !!modelData.favorite
                                onToggledFavorite: function(value) {
                                    controller.setFavorite(modelData.tmdb_id, value)
                                }
                            }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            objectName: "showsContinueSection"
            visible: page.kind === "tv" && !!page.continueModelController
            width: parent.width
            spacing: Tokens.Theme.spaceMd
            SectionHeader { title: "Devam Et"; Layout.fillWidth: true }
            BusyIndicator {
                visible: !!page.continueModelController && page.continueModelController.busy
                running: visible
            }
            Flow {
                Layout.fillWidth: true
                Layout.preferredHeight: implicitHeight
                spacing: Tokens.Theme.spaceMd
                Repeater {
                    model: page.continueModelController ? page.continueModelController.items : []
                    ContinueWatchingCard {
                        width: Math.min(510, parent.width)
                        itemData: modelData
                        controller: page.continueModelController
                        busy: page.continueModelController.busy
                        onOpened: function(tmdbId) { page.mediaSelected(tmdbId) }
                        onWatched: function(tmdbId, seasonNumber, episodeNumber) {
                            page.continueModelController.markWatched(tmdbId, seasonNumber, episodeNumber)
                        }
                    }
                }
            }
            Label {
                Layout.fillWidth: true
                visible: !!page.continueModelController && !page.continueModelController.busy
                         && page.continueModelController.items.length === 0
                text: page.continueModelController ? page.continueModelController.error
                      || "İzlemeye devam edebileceğin dizi yok." : ""
                color: Tokens.Theme.textMuted
            }
            IzlekButton {
                visible: !!page.continueModelController
                         && !!page.continueModelController.error
                enabled: !!page.continueModelController
                         && !page.continueModelController.busy
                text: "Devam Et'i Yenile"
                variant: "secondary"
                onClicked: page.continueModelController.refresh()
            }
        }
    }
    }
    LibraryBulkDialog {
        id: bulkDialog
        objectName: "libraryBulkDialog"
        controller: page.controller
    }
}
