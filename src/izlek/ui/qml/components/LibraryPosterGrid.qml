import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

GridView {
    id: grid
    property var items: []
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
        required property var modelData
        width: Math.min(142, grid.cellWidth - Tokens.Theme.spaceSm)
        height: 274
        mediaTitle: modelData.title || ""
        year: modelData.year || ""
        posterSource: modelData.poster || ""
        status: modelData.status || ""
        progress: typeof modelData.progress === "number" ? modelData.progress : -1
        progressText: modelData.progress_text || ""
        favorite: !!modelData.favorite
        favoriteEnabled: true
        Component.onCompleted: Qt.callLater(function() {
            grid.posterRequested(modelData.tmdb_id)
        })
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
