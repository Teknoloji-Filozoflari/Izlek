import QtQuick

LibraryPage {
    kind: "tv"
    signal tvSelected(int tmdbId)
    onMediaSelected: function(tmdbId) { tvSelected(tmdbId) }
}
