import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

PosterCard {
    id: card
    property var media: ({})
    property var quickLibraryController: null
    property var dismissController: null
    readonly property string libraryState: quickLibraryController
        ? (quickLibraryController.states[media.mediaType + ":" + media.id] || "") : ""
    mediaTitle: media && media.title ? String(media.title) : ""
    year: media && media.year ? String(media.year) : ""
    score: media && typeof media.score === "number" ? media.score : -1
    posterSource: media && media.poster ? media.poster : ""
    status: media && media.status ? String(media.status) : ""
    progress: media && typeof media.progress === "number" ? media.progress : -1
    progressText: media && media.progressText && !(score >= 0 && String(media.progressText).startsWith("TMDb "))
                  ? String(media.progressText) : ""
    footerHeight: quickLibraryController ? Tokens.Theme.controlHeight + Tokens.Theme.spaceSm : 0

    IzlekButton {
        objectName: "dismissRecommendationButton"
        visible: card.dismissController !== null
        enabled: visible && !card.dismissController.busy
        x: card.width - width - Tokens.Theme.spaceSm
        y: Tokens.Theme.spaceSm
        width: 34
        height: 34
        text: "⊘"
        variant: "secondary"
        Accessible.name: card.mediaTitle + " · Bir daha önerme"
        ToolTip.visible: hovered
        ToolTip.text: "Bir daha önerme"
        onClicked: card.dismissController.setDismissed(card.media, true)
    }

    IzlekButton {
        id: quickButton
        objectName: "quickLibraryAdd"
        visible: card.quickLibraryController !== null
        x: Tokens.Theme.spaceXs
        y: card.height - height - Tokens.Theme.spaceSm
        width: card.width - 2 * Tokens.Theme.spaceXs
        height: Tokens.Theme.controlHeight
        text: card.libraryState === "added" ? "✓ Kütüphanede"
              : card.libraryState === "adding" ? "Ekleniyor…" : "+ Kütüphaneye Ekle"
        variant: "secondary"
        enabled: card.libraryState === ""
        Accessible.name: card.mediaTitle + " · " + text
        onClicked: card.quickLibraryController.add(card.media)
        contentItem: Text {
            text: quickButton.text
            color: quickButton.enabled ? Tokens.Theme.accent : Tokens.Theme.textMuted
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
                          : Tokens.Theme.accent
        }
    }
}
