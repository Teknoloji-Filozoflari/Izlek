import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property string pageTitle: "Ana Sayfa"
    property var controller
    property var favoritesModelController
    property var movieLibraryModelController
    property var tvLibraryModelController
    property var statisticsModelController
    property bool showAllFavorites: false
    readonly property int movieTotal: movieLibraryModelController.stats.total || 0
    readonly property int tvTotal: tvLibraryModelController.stats.total || 0
    readonly property int trackedTotal: movieTotal + tvTotal
    readonly property int plannedTotal: (movieLibraryModelController.stats.planned || 0) + (tvLibraryModelController.stats.planned || 0)
    readonly property int watchingTotal: (movieLibraryModelController.stats.watching || 0) + (tvLibraryModelController.stats.watching || 0)
    readonly property int watchedTotal: (movieLibraryModelController.stats.watched || 0) + (tvLibraryModelController.stats.watched || 0)
    readonly property var viewingStats: statisticsModelController.stats || ({})
    readonly property bool hasLocalData: trackedTotal > 0 || favoritesModelController.items.length > 0 || controller.items.length > 0
    signal tvSelected(int tmdbId)
    signal favoriteSelected(string kind, int tmdbId)
    signal searchRequested()
    signal moviesRequested()
    signal showsRequested()
    color: Tokens.Theme.background

    function refreshDashboard() {
        controller.refresh()
        favoritesModelController.refresh()
        movieLibraryModelController.refresh()
        tvLibraryModelController.refresh()
        statisticsModelController.refresh()
    }

    function durationText(minutes) {
        if (minutes === undefined || minutes === null)
            return "—"
        var hours = Math.floor(minutes / 60)
        var remaining = minutes % 60
        return hours > 0 ? hours + " sa " + remaining + " dk" : remaining + " dk"
    }

    function missingRuntimeText(movieCount, episodeCount) {
        var parts = []
        if (movieCount > 0)
            parts.push(movieCount + " film")
        if (episodeCount > 0)
            parts.push(episodeCount + " bölüm")
        return parts.length > 0 ? parts.join(", ") + " süresi eksik"
                                : "Yerel veriden hesaplandı"
    }

    Component.onCompleted: refreshDashboard()
    onVisibleChanged: { if (visible) refreshDashboard() }

    ScrollView {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceLg
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Tokens.Theme.spaceLg

            RowLayout {
                Layout.fillWidth: true
                spacing: Tokens.Theme.spaceMd
                Label {
                    text: "Ana Sayfa"
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textHeading
                    font.weight: Tokens.Theme.weightDemiBold
                }
                Item { Layout.fillWidth: true }
                SearchField {
                    id: dashboardSearch
                    objectName: "dashboardSearch"
                    Layout.preferredWidth: Math.min(390, Math.max(240, page.width * 0.36))
                    placeholderText: "Film veya dizi ara · Ctrl+K"
                    readOnly: true
                    onPressed: function(event) {
                        event.accepted = true
                        page.searchRequested()
                    }
                    onActiveFocusChanged: { if (activeFocus) page.searchRequested() }
                }
            }

            RowLayout {
                objectName: "dashboardQuickEntry"
                Layout.fillWidth: true
                spacing: Tokens.Theme.spaceMd
                Label { text: "Hızlı giriş"; color: Tokens.Theme.textSecondary }
                IzlekButton {
                    objectName: "dashboardMovies"
                    text: "Filmler"
                    variant: "secondary"
                    onClicked: page.moviesRequested()
                }
                IzlekButton {
                    objectName: "dashboardShows"
                    text: "Diziler"
                    variant: "secondary"
                    onClicked: page.showsRequested()
                }
                Item { Layout.fillWidth: true }
            }

            Rectangle {
                objectName: "emptyDashboard"
                visible: !controller.busy && !movieLibraryModelController.busy
                         && !tvLibraryModelController.busy && !hasLocalData
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(280, page.height - 180)
                color: Tokens.Theme.surface
                radius: Tokens.Theme.radiusLg
                border.color: Tokens.Theme.border
                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 2 * Tokens.Theme.spaceXl, 460)
                    spacing: Tokens.Theme.spaceMd
                    Label {
                        Layout.alignment: Qt.AlignHCenter
                        text: "İzlek'e hoş geldin"
                        color: Tokens.Theme.textPrimary
                        font.pixelSize: Tokens.Theme.textHeading
                        font.weight: Tokens.Theme.weightDemiBold
                    }
                    Label {
                        objectName: "emptyDashboardMessage"
                        Layout.fillWidth: true
                        text: "Film veya dizi arayarak İzlek'e eklemeye başla."
                        color: Tokens.Theme.textSecondary
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                    IzlekButton {
                        Layout.alignment: Qt.AlignHCenter
                        text: "Aramayı Aç"
                        onClicked: page.searchRequested()
                    }
                }
            }

            ColumnLayout {
                visible: hasLocalData
                Layout.fillWidth: true
                spacing: Tokens.Theme.spaceLg

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: "Devam Et"
                        color: Tokens.Theme.textPrimary
                        font.pixelSize: Tokens.Theme.textEmpty
                        font.weight: Tokens.Theme.weightDemiBold
                    }
                    Item { Layout.fillWidth: true }
                    Label {
                        visible: controller.items.length > 0
                        text: controller.items.length + " dizi"
                        color: Tokens.Theme.textMuted
                        font.pixelSize: Tokens.Theme.textSmall
                    }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: controller.items.length > 0
                                           ? Math.min(460, 232 * Math.ceil(controller.items.length / Math.max(1, Math.floor(width / 520))))
                                           : 106
                    color: Tokens.Theme.surface
                    radius: Tokens.Theme.radiusLg
                    border.color: Tokens.Theme.border
                    Flow {
                        id: cardsFlow
                        anchors.fill: parent
                        anchors.margins: Tokens.Theme.spaceSm
                        spacing: Tokens.Theme.spaceMd
                        Repeater {
                            model: controller.items
                            ContinueWatchingCard {
                                parent: cardsFlow
                                width: Math.min(510, cardsFlow.width)
                                itemData: modelData
                                busy: controller.busy
                                onOpened: function(tmdbId) { page.tvSelected(tmdbId) }
                                onWatched: function(tmdbId, seasonNumber, episodeNumber) {
                                    controller.markWatched(tmdbId, seasonNumber, episodeNumber)
                                }
                            }
                        }
                    }
                    Label {
                        anchors.centerIn: parent
                        visible: !controller.busy && controller.items.length === 0
                        text: controller.error || "İzlemeye devam edebileceğin dizi yok."
                        color: Tokens.Theme.textSecondary
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: page.width >= 1080 ? 2 : 1
                    columnSpacing: Tokens.Theme.spaceLg
                    rowSpacing: Tokens.Theme.spaceLg

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 218
                        color: Tokens.Theme.surface
                        radius: Tokens.Theme.radiusLg
                        border.color: Tokens.Theme.border
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: Tokens.Theme.spaceMd
                            spacing: Tokens.Theme.spaceSm
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: "Favorilerim"
                                    color: Tokens.Theme.textPrimary
                                    font.pixelSize: Tokens.Theme.textEmpty
                                    font.weight: Tokens.Theme.weightDemiBold
                                }
                                Item { Layout.fillWidth: true }
                                IzlekButton {
                                    objectName: "allFavoritesButton"
                                    visible: favoritesModelController.items.length > 6
                                    text: page.showAllFavorites ? "Daha Az Göster" : "Tümünü Gör"
                                    variant: "ghost"
                                    onClicked: page.showAllFavorites = !page.showAllFavorites
                                }
                            }
                            Label {
                                visible: favoritesModelController.items.length === 0
                                text: favoritesModelController.error || "Henüz favorin yok."
                                color: Tokens.Theme.textSecondary
                            }
                            ListView {
                                id: favoritesStrip
                                objectName: "dashboardFavorites"
                                visible: favoritesModelController.items.length > 0
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                orientation: ListView.Horizontal
                                spacing: Tokens.Theme.spaceSm
                                clip: true
                                model: page.showAllFavorites ? favoritesModelController.items : favoritesModelController.items.slice(0, 6)
                                delegate: Rectangle {
                                    required property var modelData
                                    width: 172
                                    height: favoritesStrip.height
                                    color: Tokens.Theme.surfaceElevated
                                    radius: Tokens.Theme.radiusSm
                                    ItemDelegate {
                                        anchors.fill: parent
                                        anchors.rightMargin: Tokens.Theme.controlHeight
                                        text: modelData.title + " · " + (modelData.kind === "movie" ? "Film" : "Dizi")
                                        onClicked: page.favoriteSelected(modelData.kind, modelData.tmdb_id)
                                        contentItem: Label {
                                            text: parent.text
                                            color: Tokens.Theme.textPrimary
                                            wrapMode: Text.WordWrap
                                            maximumLineCount: 2
                                            elide: Text.ElideRight
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                        background: Item {}
                                    }
                                    FavoriteButton {
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        checked: !!modelData.favorite
                                        onToggledFavorite: function(value) {
                                            favoritesModelController.setFavorite(modelData.kind, modelData.tmdb_id, value)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        objectName: "dashboardStats"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 274
                        color: Tokens.Theme.surface
                        radius: Tokens.Theme.radiusLg
                        border.color: Tokens.Theme.border
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: Tokens.Theme.spaceMd
                            spacing: Tokens.Theme.spaceSm
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: "İstatistik Özeti"
                                    color: Tokens.Theme.textPrimary
                                    font.pixelSize: Tokens.Theme.textEmpty
                                    font.weight: Tokens.Theme.weightDemiBold
                                }
                                Item { Layout.fillWidth: true }
                                IzlekButton {
                                    objectName: "allStatisticsButton"
                                    text: "Tümünü Gör"
                                    variant: "ghost"
                                    onClicked: statisticsDialog.open()
                                }
                            }
                            GridLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                columns: 2
                                columnSpacing: Tokens.Theme.spaceSm
                                rowSpacing: Tokens.Theme.spaceSm
                                Repeater {
                                    model: [
                                        { label: "İzlenen film", value: page.viewingStats.watched_movies || 0, detail: "Yerel kütüphane" },
                                        { label: "Tamamlanan dizi", value: page.viewingStats.completed_tv || 0, detail: "Yerel kütüphane" },
                                        { label: "İzlenen bölüm", value: page.viewingStats.watched_episodes || 0, detail: "Yerel ilerleme" },
                                        { label: "Tahmini süre", value: page.durationText(page.viewingStats.estimated_total_minutes), detail: page.missingRuntimeText(page.viewingStats.missing_movie_runtime_count || 0, page.viewingStats.missing_episode_runtime_count || 0) }
                                    ]
                                    StatCard {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        label: modelData.label
                                        value: String(modelData.value)
                                        detail: modelData.detail
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: statisticsDialog
        objectName: "statisticsDialog"
        modal: true
        focus: true
        title: "İstatistikler"
        width: Math.min(560, page.width - 2 * Tokens.Theme.spaceLg)
        x: (page.width - width) / 2
        y: Math.max(Tokens.Theme.spaceLg, (page.height - height) / 2)
        padding: Tokens.Theme.spaceLg
        closePolicy: Popup.CloseOnEscape
        onOpened: statisticsCloseButton.forceActiveFocus()
        Overlay.modal: Rectangle { color: Tokens.Theme.scrim }
        header: Label {
            text: statisticsDialog.title
            color: Tokens.Theme.textPrimary
            font.pixelSize: Tokens.Theme.textEmpty
            font.weight: Tokens.Theme.weightDemiBold
            padding: Tokens.Theme.spaceLg
        }
        contentItem: ColumnLayout {
            spacing: Tokens.Theme.spaceMd
            Repeater {
                model: [
                    { label: "İzlenen film", value: page.viewingStats.watched_movies || 0 },
                    { label: "Tamamlanan dizi", value: page.viewingStats.completed_tv || 0 },
                    { label: "İzlenen bölüm", value: page.viewingStats.watched_episodes || 0 },
                    { label: "İzlenen film süresi", value: page.durationText(page.viewingStats.watched_movie_minutes) },
                    { label: "İzlenen bölüm süresi", value: page.durationText(page.viewingStats.watched_episode_minutes) },
                    { label: "Tahmini toplam süre", value: page.durationText(page.viewingStats.estimated_total_minutes) },
                    { label: "Favori film", value: page.viewingStats.favorite_movies || 0 },
                    { label: "Favori dizi", value: page.viewingStats.favorite_tv || 0 },
                    { label: "İzlenecek film", value: page.viewingStats.planned_movies || 0 },
                    { label: "İzlenecek dizi", value: page.viewingStats.planned_tv || 0 }
                ]
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Label { text: modelData.label; color: Tokens.Theme.textSecondary }
                    Item { Layout.fillWidth: true }
                    Label {
                        text: String(modelData.value)
                        color: Tokens.Theme.textPrimary
                        font.weight: Tokens.Theme.weightDemiBold
                    }
                }
            }
            Label {
                Layout.fillWidth: true
                visible: (page.viewingStats.missing_movie_runtime_count || 0) > 0
                         || (page.viewingStats.missing_episode_runtime_count || 0) > 0
                text: page.missingRuntimeText(page.viewingStats.missing_movie_runtime_count || 0, page.viewingStats.missing_episode_runtime_count || 0)
                color: Tokens.Theme.textMuted
                wrapMode: Text.WordWrap
            }
            Label {
                visible: (page.viewingStats.top_genres || []).length > 0
                text: "En çok izlenen türler"
                color: Tokens.Theme.textPrimary
                font.weight: Tokens.Theme.weightDemiBold
            }
            Flow {
                Layout.fillWidth: true
                spacing: Tokens.Theme.spaceXs
                Repeater {
                    model: page.viewingStats.top_genres || []
                    Label {
                        required property var modelData
                        text: modelData.name + " · " + modelData.count
                        color: Tokens.Theme.textSecondary
                        font.pixelSize: Tokens.Theme.textSmall
                    }
                }
            }
        }
        footer: RowLayout {
            Item { Layout.fillWidth: true }
            IzlekButton { id: statisticsCloseButton; text: "Kapat"; onClicked: statisticsDialog.close() }
        }
        background: Rectangle {
            color: Tokens.Theme.surfaceElevated
            radius: Tokens.Theme.radiusMd
            border.color: Tokens.Theme.border
        }
    }
}
