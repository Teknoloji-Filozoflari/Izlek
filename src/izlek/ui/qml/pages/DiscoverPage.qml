import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property string pageTitle: "Keşfet"
    property var controller
    readonly property var movieGenres: [
        { text: "Tüm türler", value: 0 }, { text: "Aksiyon", value: 28 },
        { text: "Animasyon", value: 16 }, { text: "Bilim Kurgu", value: 878 },
        { text: "Dram", value: 18 }, { text: "Gerilim", value: 53 },
        { text: "Komedi", value: 35 }, { text: "Suç", value: 80 },
        { text: "Korku", value: 27 }, { text: "Macera", value: 12 },
        { text: "Romantik", value: 10749 }
    ]
    readonly property var tvGenres: [
        { text: "Tüm türler", value: 0 }, { text: "Aksiyon & Macera", value: 10759 },
        { text: "Bilim Kurgu & Fantastik", value: 10765 }, { text: "Dram", value: 18 },
        { text: "Gerilim", value: 9648 }, { text: "Komedi", value: 35 },
        { text: "Suç", value: 80 }, { text: "Belgesel", value: 99 },
        { text: "Çocuk", value: 10762 }, { text: "Reality", value: 10764 }
    ]
    readonly property var countries: [
        { text: "Tüm ülkeler", value: "" }, { text: "Türkiye", value: "TR" },
        { text: "ABD", value: "US" }, { text: "Birleşik Krallık", value: "GB" },
        { text: "Almanya", value: "DE" }, { text: "Fransa", value: "FR" },
        { text: "Güney Kore", value: "KR" }, { text: "Japonya", value: "JP" }
    ]
    signal mediaSelected(string kind, int tmdbId)
    color: Tokens.Theme.background

    function applyFilters() {
        controller.applyFilters(
            mediaSelector.currentValue, yearInput.text, genreSelector.currentValue,
            countrySelector.currentValue, minScore.value, maxScore.value)
    }

    Component.onCompleted: applyFilters()
    onVisibleChanged: {
        if (visible && controller.items.length === 0 && !controller.busy)
            applyFilters()
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceLg
        spacing: Tokens.Theme.spaceLg

        Rectangle {
            id: filterPanel
            objectName: "discoverFilters"
            Layout.preferredWidth: page.width >= 1060 ? 250 : 218
            Layout.fillHeight: true
            color: Tokens.Theme.surface
            radius: Tokens.Theme.radiusLg
            border.color: Tokens.Theme.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Tokens.Theme.spaceMd
                spacing: Tokens.Theme.spaceSm
                Label {
                    text: "Filtreler"
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textEmpty
                    font.weight: Tokens.Theme.weightDemiBold
                }
                Label { text: "Medya"; color: Tokens.Theme.textSecondary }
                FilterComboBox {
                    id: mediaSelector
                    objectName: "discoverMedia"
                    Layout.fillWidth: true
                    model: [ { text: "Film", value: "movie" }, { text: "Dizi", value: "tv" } ]
                    textRole: "text"
                    valueRole: "value"
                    onActivated: {
                        genreSelector.currentIndex = 0
                        page.applyFilters()
                    }
                }
                Label { text: "Yıl"; color: Tokens.Theme.textSecondary }
                FilterTextField {
                    id: yearInput
                    objectName: "discoverYear"
                    Layout.fillWidth: true
                    placeholderText: "Örn. 2024"
                    color: Tokens.Theme.textPrimary
                    validator: IntValidator { bottom: 1888; top: 2100 }
                }
                Label { text: "Tür"; color: Tokens.Theme.textSecondary }
                FilterComboBox {
                    id: genreSelector
                    objectName: "discoverGenre"
                    Layout.fillWidth: true
                    model: mediaSelector.currentValue === "movie"
                           ? page.movieGenres : page.tvGenres
                    textRole: "text"
                    valueRole: "value"
                }
                Label { text: "Ülke"; color: Tokens.Theme.textSecondary }
                FilterComboBox {
                    id: countrySelector
                    objectName: "discoverCountry"
                    Layout.fillWidth: true
                    model: page.countries
                    textRole: "text"
                    valueRole: "value"
                }
                Label {
                    text: "Minimum puan: " + (minScore.value / 10).toFixed(1)
                    color: Tokens.Theme.textSecondary
                }
                FilterSpinBox {
                    id: minScore
                    objectName: "discoverMinScore"
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    stepSize: 5
                    value: 0
                    textFromValue: function(value) { return (value / 10).toFixed(1) }
                    valueFromText: function(text) { return Math.round(Number(text) * 10) }
                }
                Label {
                    text: "Maximum puan: " + (maxScore.value / 10).toFixed(1)
                    color: Tokens.Theme.textSecondary
                }
                FilterSpinBox {
                    id: maxScore
                    objectName: "discoverMaxScore"
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    stepSize: 5
                    value: 100
                    textFromValue: function(value) { return (value / 10).toFixed(1) }
                    valueFromText: function(text) { return Math.round(Number(text) * 10) }
                }
                Label {
                    Layout.fillWidth: true
                    text: "Sıralama: TMDb puanı · En az 100 oy"
                    color: Tokens.Theme.textMuted
                    font.pixelSize: Tokens.Theme.textSmall
                    wrapMode: Text.WordWrap
                }
                Item { Layout.fillHeight: true }
                IzlekButton {
                    objectName: "applyDiscoverFilters"
                    Layout.fillWidth: true
                    text: "Uygula"
                    enabled: !controller.busy && minScore.value <= maxScore.value
                    onClicked: page.applyFilters()
                }
                IzlekButton {
                    objectName: "clearDiscoverFilters"
                    Layout.fillWidth: true
                    text: "Temizle"
                    variant: "secondary"
                    enabled: !controller.busy
                    onClicked: {
                        yearInput.text = ""
                        genreSelector.currentIndex = 0
                        countrySelector.currentIndex = 0
                        minScore.value = 0
                        maxScore.value = 100
                        page.applyFilters()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Tokens.Theme.surface
            radius: Tokens.Theme.radiusLg
            border.color: Tokens.Theme.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Tokens.Theme.spaceMd
                spacing: Tokens.Theme.spaceMd
                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: controller.mediaKind === "movie" ? "Filmleri Keşfet" : "Dizileri Keşfet"
                        color: Tokens.Theme.textPrimary
                        font.pixelSize: Tokens.Theme.textHeading
                        font.weight: Tokens.Theme.weightDemiBold
                    }
                    Item { Layout.fillWidth: true }
                    Label {
                        visible: !controller.busy && controller.items.length > 0
                        text: "Sayfa " + controller.page + " / " + controller.totalPages
                        color: Tokens.Theme.textMuted
                    }
                }
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    LoadingState {
                        anchors.centerIn: parent
                        visible: controller.busy
                        count: 4
                        skeletonPosterHeight: 210
                    }
                    EmptyState {
                        anchors.centerIn: parent
                        visible: !controller.busy && !!controller.error
                        title: "Keşfet yüklenemedi"
                        description: controller.error
                        actionText: "Tekrar Dene"
                        onActionRequested: page.applyFilters()
                    }
                    EmptyState {
                        anchors.centerIn: parent
                        visible: !controller.busy && !controller.error
                                 && controller.items.length === 0
                        title: "Sonuç bulunamadı"
                        description: "Filtreleri genişletip tekrar deneyin."
                    }
                    MediaGrid {
                        id: resultsGrid
                        objectName: "discoverResults"
                        anchors.fill: parent
                        visible: !controller.busy && controller.items.length > 0
                        items: controller.items
                        onMediaActivated: function(media) {
                            page.mediaSelected(media.mediaType, media.id)
                        }
                    }
                }
                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: Tokens.Theme.spaceSm
                    IzlekButton {
                        objectName: "discoverPrevious"
                        text: "← Önceki"
                        variant: "secondary"
                        enabled: !controller.busy && controller.page > 1
                        onClicked: controller.goToPage(controller.page - 1)
                    }
                    Label {
                        text: controller.page + " / " + controller.totalPages
                        color: Tokens.Theme.textSecondary
                    }
                    IzlekButton {
                        objectName: "discoverNext"
                        text: "Sonraki →"
                        variant: "secondary"
                        enabled: !controller.busy && controller.page < controller.totalPages
                        onClicked: controller.goToPage(controller.page + 1)
                    }
                }
            }
        }
    }
}
