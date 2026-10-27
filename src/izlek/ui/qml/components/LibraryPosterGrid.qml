import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

GridView {
    id: grid
    property var items: []
    property var controller: null
    property bool compact: false
    property bool selectionMode: false
    property var selectedIds: []
    readonly property int targetCardWidth: compact ? Tokens.Theme.cardCompactWidth : Tokens.Theme.cardWidth
    readonly property real posterCardWidth: Math.min(targetCardWidth, cellWidth - Tokens.Theme.spaceSm)
    readonly property int columns: Math.max(1, Math.floor(width / (targetCardWidth + Tokens.Theme.spaceSm)))
    signal mediaActivated(int tmdbId)
    signal favoriteToggled(int tmdbId, bool favorite)
    signal posterRequested(int tmdbId)
    signal reorderRequested(int sourceId, int targetId)
    signal selectionToggled(int tmdbId)
    model: items
    cellWidth: width / columns
    cellHeight: Math.round(posterCardWidth * 1.5) + Tokens.Theme.cardInfoHeight + Tokens.Theme.gridGap
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true

    delegate: PosterCard {
        id: posterCard
        required property var modelData
        property string resolvedPoster: modelData.poster || ""
        width: grid.posterCardWidth
        height: grid.cellHeight - Tokens.Theme.gridGap
        mediaTitle: modelData.title || ""
        year: modelData.year || ""
        score: typeof modelData.score === "number" ? modelData.score : -1
        posterSource: resolvedPoster
        posterLoading: !resolvedPoster && !!modelData.poster_path
        Connections {
            target: grid.controller
            function onPosterAvailable(tmdbId, url) {
                if (tmdbId === posterCard.modelData.tmdb_id)
                    posterCard.resolvedPoster = url
            }
        }
        status: modelData.status || ""
        progress: typeof modelData.episode_count === "number" ? Math.max(0, modelData.progress)
                  : typeof modelData.progress === "number" ? modelData.progress : -1
        progressText: typeof modelData.episode_count === "number"
            ? modelData.watched_count + " / " + (modelData.episode_count || "—") + " bölüm"
            : modelData.progress_text || ""
        favorite: !!modelData.favorite
        favoriteEnabled: true
        selectionEnabled: grid.selectionMode
        selected: grid.selectedIds.indexOf(modelData.tmdb_id) >= 0
        personalRating: modelData.personal_rating || 0
        onSelectionToggled: grid.selectionToggled(modelData.tmdb_id)
        reorderEnabled: !!grid.controller && !grid.controller.busy
                        && !grid.controller.reordering && grid.items.length > 1
                        && !grid.selectionMode && !grid.controller.filtersActive && !grid.controller.batchBusy
        reorderView: grid
        onReorderDropped: function(position) {
            var point = grid.mapFromItem(null, position.x, position.y)
            if (point.x < 0 || point.x >= grid.width || point.y < 0 || point.y >= grid.height) return
            var index = grid.indexAt(point.x + grid.contentX, point.y + grid.contentY)
            if (index >= 0 && index < grid.items.length)
                grid.reorderRequested(modelData.tmdb_id, grid.items[index].tmdb_id)
        }
        function requestPosterIfNeeded() {
            if (modelData && !modelData.poster)
                Qt.callLater(function() {
                    if (modelData && !modelData.poster)
                        grid.posterRequested(modelData.tmdb_id)
                })
        }
        Component.onCompleted: requestPosterIfNeeded()
        onModelDataChanged: {
            resolvedPoster = modelData.poster || ""
            requestPosterIfNeeded()
        }
        onVisibleChanged: { if (visible) requestPosterIfNeeded() }
        onActivated: {
            if (grid.selectionMode) grid.selectionToggled(modelData.tmdb_id)
            else grid.mediaActivated(modelData.tmdb_id)
        }
        onFavoriteToggled: function(value) {
            grid.favoriteToggled(modelData.tmdb_id, value)
        }
    }

    ScrollBar.vertical: ScrollBar {
        policy: grid.contentHeight > grid.height ? ScrollBar.AsNeeded
                                                 : ScrollBar.AlwaysOff
    }
}
