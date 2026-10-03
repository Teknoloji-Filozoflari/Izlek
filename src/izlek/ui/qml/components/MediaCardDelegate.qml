import QtQuick

PosterCard {
    property var media: ({})
    mediaTitle: media && media.title ? String(media.title) : ""
    year: media && media.year ? String(media.year) : ""
    posterSource: media && media.poster ? media.poster : ""
    status: media && media.status ? String(media.status) : ""
    progress: media && typeof media.progress === "number" ? media.progress : -1
    progressText: media && media.progressText ? String(media.progressText) : ""
}
