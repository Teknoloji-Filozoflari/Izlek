import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

GridView {
    id: grid
    property var items: []
    property var controller: null
    readonly property int columns: Math.max(1, Math.floor(width / 154))
    signal mediaActivated(int tmdbId)
    signal favoriteToggled(int tmdbId, bool favorite)
    signal posterRequested(int tmdbId)
    model: items
    cellWidth: width / columns
    cellHeight: 286
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true

    delegate: PosterCard {
        id: posterCard
        required property var modelData
        property string resolvedPoster: modelData.poster || ""
        width: Math.min(142, grid.cellWidth - Tokens.Theme.spaceSm)
        height: 274
        mediaTitle: modelData.title || ""
        year: modelData.year || ""
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
        onActivated: grid.mediaActivated(modelData.tmdb_id)
        onFavoriteToggled: function(value) {
            grid.favoriteToggled(modelData.tmdb_id, value)
        }
    }

    ScrollBar.vertical: ScrollBar {
        policy: grid.contentHeight > grid.height ? ScrollBar.AsNeeded
                                                 : ScrollBar.AlwaysOff
    }
}
