import QtQuick
import "../theme" as Tokens

PosterCard {
    id: card
    property var media: ({})
    property var quickLibraryController: null
    readonly property string libraryState: quickLibraryController
        ? (quickLibraryController.states[media.mediaType + ":" + media.id] || "") : ""
    mediaTitle: media && media.title ? String(media.title) : ""
    year: media && media.year ? String(media.year) : ""
    posterSource: media && media.poster ? media.poster : ""
    status: media && media.status ? String(media.status) : ""
    progress: media && typeof media.progress === "number" ? media.progress : -1
    progressText: media && media.progressText ? String(media.progressText) : ""

    IzlekButton {
        id: quickButton
        objectName: "quickLibraryAdd"
        visible: card.quickLibraryController !== null
        x: 0
        y: card.height + Tokens.Theme.spaceSm
        width: card.width
        height: Tokens.Theme.controlHeight
        text: card.libraryState === "added" ? "✓ Kütüphanede"
              : card.libraryState === "adding" ? "Ekleniyor…" : "+ Kütüphaneye Ekle"
        variant: "secondary"
        enabled: card.libraryState === ""
        Accessible.name: card.mediaTitle + " · " + text
        onClicked: card.quickLibraryController.add(card.media)
        contentItem: Text {
            text: quickButton.text
            color: quickButton.enabled ? Tokens.Theme.statsAccent : Tokens.Theme.textMuted
            font.pixelSize: Tokens.Theme.textSmall
            font.weight: Tokens.Theme.weightDemiBold
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: Tokens.Theme.radiusSm
            color: quickButton.hovered ? Tokens.Theme.hoverSurface : Tokens.Theme.surface
            border.width: quickButton.activeFocus ? 2 : 1
            border.color: card.libraryState === "added" ? Tokens.Theme.border
                          : Tokens.Theme.statsAccent
        }
    }
}
