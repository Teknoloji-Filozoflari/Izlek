import QtQuick

LibraryPage {
    kind: "movie"
    signal movieSelected(int tmdbId)
    onMediaSelected: function(tmdbId) { movieSelected(tmdbId) }
}
