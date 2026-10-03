import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "theme" as Tokens

ApplicationWindow {
    id: gallery
    objectName: "componentsGallery"
    title: "İzlek · Bileşen Galerisi"
    width: 1366
    height: 768
    minimumWidth: 900
    minimumHeight: 650
    visible: false
    color: Tokens.Theme.background

    readonly property var demoMedia: [
        { id: 1, title: "Night Line", year: "2025", poster: Qt.resolvedUrl("../../resources/images/night-line.svg"), status: "WATCHING", progress: 0.46, progressText: "6 / 13 bölüm" },
        { id: 2, title: "Orbit", year: "2024", poster: Qt.resolvedUrl("../../resources/images/orbit.svg"), status: "WATCHED" },
        { id: 3, title: "Afterlight", year: "2023", poster: Qt.resolvedUrl("../../resources/images/afterlight.svg"), status: "PLANNED" },
        { id: 4, title: "Northbound", year: "2025", poster: Qt.resolvedUrl("../../resources/images/northbound.svg"), status: "WATCHING", progress: 0.72, progressText: "18 / 25 bölüm" },
        { id: 5, title: "The Quiet Signal", year: "2022", poster: Qt.resolvedUrl("../../resources/images/orbit.svg") },
        { id: 6, title: "Last Platform", year: "2021", poster: Qt.resolvedUrl("../../resources/images/night-line.svg"), status: "WATCHED" },
        { id: 7, title: "Under the Pines", year: "2024", poster: Qt.resolvedUrl("../../resources/images/northbound.svg"), status: "PLANNED" },
        { id: 8, title: "A Long Evening", year: "2020", poster: Qt.resolvedUrl("../../resources/images/afterlight.svg") },
        { id: 9, title: "Blue Frequency", year: "2026", poster: Qt.resolvedUrl("../../resources/images/orbit.svg"), status: "WATCHING", progress: 0.25, progressText: "3 / 12 bölüm" },
        { id: 10, title: "The Crossing", year: "2023", poster: Qt.resolvedUrl("../../resources/images/night-line.svg") },
        { id: 11, title: "Beyond the Ridge", year: "2022", poster: Qt.resolvedUrl("../../resources/images/northbound.svg"), status: "WATCHED" },
        { id: 12, title: "Dawn Window", year: "2025", poster: Qt.resolvedUrl("../../resources/images/afterlight.svg"), status: "PLANNED" },
        { id: 13, title: "Untitled Example", year: "2026", poster: "" },
        { id: 14, title: "Second Orbit", year: "2021", poster: Qt.resolvedUrl("../../resources/images/orbit.svg") },
        { id: 15, title: "Morning Platform", year: "2024", poster: Qt.resolvedUrl("../../resources/images/night-line.svg"), status: "WATCHING", progress: 0.5, progressText: "5 / 10 bölüm" },
        { id: 16, title: "The Long Way", year: "2023", poster: Qt.resolvedUrl("../../resources/images/northbound.svg") },
        { id: 17, title: "City at Dusk", year: "2026", poster: Qt.resolvedUrl("../../resources/images/afterlight.svg"), status: "PLANNED" },
        { id: 18, title: "The Far Side", year: "2022", poster: Qt.resolvedUrl("../../resources/images/orbit.svg"), status: "WATCHED" }
    ]

    ScrollView {
        id: scroll
        objectName: "galleryScroll"
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: Math.min(scroll.availableWidth - 2 * Tokens.Theme.spaceXl, 1720)
            x: (scroll.availableWidth - width) / 2
            spacing: Tokens.Theme.spaceXl

            SectionHeader {
                Layout.fillWidth: true
                Layout.topMargin: Tokens.Theme.spaceXl
                title: "Bileşen Galerisi"
                subtitle: "İzlek arayüz öğeleri · yerel örnek içerik"
            }

            Flow {
                Layout.fillWidth: true
                Layout.preferredHeight: childrenRect.height
                spacing: Tokens.Theme.spaceSm
                IzlekButton { text: "Birincil İşlem"; onClicked: toast.show("İşlem seçildi", "success") }
                IzlekButton { text: "İkincil"; variant: "secondary" }
                IzlekButton { text: "Düz Buton"; variant: "ghost" }
                IzlekButton { text: "Sil"; variant: "danger" }
                IconButton {
                    iconSource: Qt.resolvedUrl("../../resources/icons/search.svg")
                    toolTipText: "Arama"
                    onClicked: searchField.forceActiveFocus()
                }
                FavoriteButton { objectName: "galleryFavorite" }
                SearchField { id: searchField; objectName: "gallerySearch"; width: 320 }
                IzlekButton { text: "Dialog Aç"; variant: "secondary"; onClicked: sampleDialog.open() }
                IzlekButton { text: "Bildirim Göster"; variant: "secondary"; onClicked: toast.show("Kütüphaneniz güncel", "success") }
            }

            Flow {
                Layout.fillWidth: true
                Layout.preferredHeight: childrenRect.height
                spacing: Tokens.Theme.spaceSm
                Badge { text: "İzlenecek" }
                Badge { text: "İzleniyor"; tone: "accent" }
                Badge { text: "İzlendi"; tone: "success" }
                Badge { text: "Uyarı"; tone: "warning" }
                Badge { text: "Hata"; tone: "danger" }
                SegmentedControl { options: ["Film", "Dizi"]; currentIndex: 0 }
                StatusSelector { objectName: "galleryStatus"; status: "WATCHING" }
            }

            SectionHeader {
                Layout.fillWidth: true
                title: "Medya Kartları"
                subtitle: "Poster, durum ve bölüm ilerlemesi"
                actionText: "Tümünü Gör"
                onActionTriggered: toast.show("Tüm medya seçildi")
            }
            MediaGrid {
                id: grid
                objectName: "galleryGrid"
                Layout.fillWidth: true
                Layout.preferredHeight: Math.ceil(demoMedia.length / columns) * cellHeight
                items: gallery.demoMedia
                onMediaActivated: function(media) { toast.show(media.title + " seçildi") }
            }

            SectionHeader {
                Layout.fillWidth: true
                title: "Yatay Medya Şeridi"
                subtitle: "Kompakt bölümler için alternatif düzen"
            }
            HorizontalMediaStrip {
                objectName: "galleryStrip"
                Layout.fillWidth: true
                Layout.preferredHeight: Tokens.Theme.cardHeight
                items: gallery.demoMedia
                onMediaActivated: function(media) { toast.show(media.title + " seçildi") }
            }

            SectionHeader { Layout.fillWidth: true; title: "İstatistik Kartları" }
            RowLayout {
                Layout.fillWidth: true
                spacing: Tokens.Theme.gridGap
                StatCard { Layout.fillWidth: true; label: "İzlenen Film"; value: "28"; detail: "Bu yıl 9 film" }
                StatCard { Layout.fillWidth: true; label: "İzlenen Dizi"; value: "12"; detail: "4 dizi sürüyor" }
                StatCard { Layout.fillWidth: true; label: "Bölüm"; value: "146"; detail: "Toplam" }
                StatCard { Layout.fillWidth: true; label: "İzlenecek"; value: "34"; detail: "Film ve dizi" }
            }

            SectionHeader { Layout.fillWidth: true; title: "Durumlar" }
            RowLayout {
                Layout.fillWidth: true
                spacing: Tokens.Theme.gridGap
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 220
                    color: Tokens.Theme.surface
                    radius: Tokens.Theme.radiusMd
                    EmptyState { anchors.fill: parent; title: "Listen boş"; description: "İçerikler burada görünecek"; actionText: "İçerik Ekle"; onActionRequested: toast.show("İçerik ekle seçildi") }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 220
                    color: Tokens.Theme.surface
                    radius: Tokens.Theme.radiusMd
                    ErrorState { anchors.fill: parent; onActionRequested: toast.show("Yeniden denendi") }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 220
                    color: Tokens.Theme.surface
                    radius: Tokens.Theme.radiusMd
                    LoadingState { anchors.centerIn: parent; width: Math.min(parent.width - 32, 190); height: 190; count: 1; skeletonPosterHeight: 132 }
                }
            }
            Item { Layout.preferredHeight: Tokens.Theme.spaceXl }
        }
    }

    IzlekDialog {
        id: sampleDialog
        objectName: "galleryDialog"
        parent: Overlay.overlay
        title: "Örnek Dialog"
        message: "Bu pencere yalnızca bileşen önizlemesi içindir."
        onConfirmed: toast.show("Onaylandı", "success")
    }
    Toast { id: toast; objectName: "galleryToast"; parent: Overlay.overlay }
}
