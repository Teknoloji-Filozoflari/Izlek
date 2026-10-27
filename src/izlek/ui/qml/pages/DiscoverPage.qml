import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components" as Components
import "../theme" as Tokens

Rectangle {
    id: page
    property string pageTitle: (i18n.revision, i18n.t("page.home"))
    property var controller
    property var searchModelController
    readonly property var libraryActions: quickLibraryController
    property string searchMode: "title"
    property bool restoringPerson: false
    readonly property bool personMode: searchMode !== "title"
    readonly property bool directorMode: searchMode === "director"
    readonly property bool choosingPerson: personMode && !searchModelController.selectedPerson.id
    readonly property bool searching: personMode || searchInput.text.trim().length > 0
    readonly property var displayedItems: searching
        ? searchModelController.movies.concat(searchModelController.shows) : controller.items
    readonly property bool resultsBusy: searching ? searchModelController.busy : controller.busy
    readonly property string resultsError: searching ? searchModelController.error : controller.error
    readonly property bool filterPopupOpen: mediaSelector.popup.visible
        || genreSelector.popup.visible || countrySelector.popup.visible
    readonly property int _i18n: i18n.revision
    readonly property var movieGenres: {
        const _ = _i18n
        return [
            { text: i18n.t("discover.all_genres"), value: 0 }, { text: i18n.t("genre.action"), value: 28 },
            { text: i18n.t("genre.animation"), value: 16 }, { text: i18n.t("genre.scifi"), value: 878 },
            { text: i18n.t("genre.drama"), value: 18 }, { text: i18n.t("genre.thriller"), value: 53 },
            { text: i18n.t("genre.comedy"), value: 35 }, { text: i18n.t("genre.crime"), value: 80 },
            { text: i18n.t("genre.horror"), value: 27 }, { text: i18n.t("genre.adventure"), value: 12 },
            { text: i18n.t("genre.romance"), value: 10749 }
        ]
    }
    readonly property var tvGenres: {
        const _ = _i18n
        return [
            { text: i18n.t("discover.all_genres"), value: 0 }, { text: i18n.t("genre.action_adventure"), value: 10759 },
            { text: i18n.t("genre.scifi_fantasy"), value: 10765 }, { text: i18n.t("genre.drama"), value: 18 },
            { text: i18n.t("genre.mystery"), value: 9648 }, { text: i18n.t("genre.comedy"), value: 35 },
            { text: i18n.t("genre.crime"), value: 80 }, { text: i18n.t("genre.documentary"), value: 99 },
            { text: i18n.t("genre.kids"), value: 10762 }, { text: i18n.t("genre.reality"), value: 10764 }
        ]
    }
    readonly property var countries: {
        const _ = _i18n
        return [
            { text: i18n.t("discover.all_countries"), value: "" }, { text: i18n.t("country.TR"), value: "TR" },
            { text: i18n.t("country.US"), value: "US" }, { text: i18n.t("country.GB"), value: "GB" },
            { text: i18n.t("country.DE"), value: "DE" }, { text: i18n.t("country.FR"), value: "FR" },
            { text: i18n.t("country.KR"), value: "KR" }, { text: i18n.t("country.JP"), value: "JP" }
        ]
    }
    signal mediaSelected(string kind, int tmdbId)
    signal searchRequested()
    color: Tokens.Theme.background

    function applyFilters() {
        controller.applyFilters(
            mediaSelector.currentValue, yearInput.text, genreSelector.currentValue,
            countrySelector.currentValue, minScore.value, maxScore.value)
    }

    function updateSearchMedia() {
        searchDebounce.stop()
        if (personMode) {
            if (searchModelController.selectedPerson.id)
                searchModelController.selectPerson(searchModelController.selectedPerson.id, mediaSelector.currentValue, searchMode)
            else if (searchInput.text.trim().length >= 3) searchDebounce.start()
            return
        }
        searchModelController.setMediaType(mediaSelector.currentValue)
        if (searchInput.text.trim().length >= 3) searchDebounce.start()
    }

    function showActor(personId, name, kind) {
        restoringPerson = true
        searchMode = "actor"
        mediaSelector.currentIndex = kind === "tv" ? 1 : 0
        searchInput.text = name
        restoringPerson = false
        searchDebounce.stop()
        searchModelController.openActor(personId, name, kind)
    }

    function focusSearch() { searchInput.forceActiveFocus() }

    function runSearch() {
        if (personMode) {
            if (searchModelController.selectedPerson.id)
                searchModelController.selectPerson(searchModelController.selectedPerson.id, mediaSelector.currentValue, searchMode)
            else searchModelController.searchPeople(searchInput.text, searchMode)
            return
        }
        searchModelController.setMediaType(mediaSelector.currentValue)
        searchModelController.search(searchInput.text)
    }

    Timer {
        id: searchDebounce
        interval: 300
        onTriggered: page.runSearch()
    }

    Component.onCompleted: {
        quickLibraryController.refresh()
        updateSearchMedia()
        applyFilters()
    }
    onVisibleChanged: {
        if (visible) quickLibraryController.refresh()
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
                    text: (i18n.revision, i18n.t("discover.filters"))
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textEmpty
                    font.weight: Tokens.Theme.weightDemiBold
                }
                Label { text: (i18n.revision, i18n.t("discover.media")); color: Tokens.Theme.textSecondary }
                FilterComboBox {
                    id: mediaSelector
                    objectName: "discoverMedia"
                    Layout.fillWidth: true
                    model: [ { text: (i18n.revision, i18n.t("common.movie")), value: "movie" }, { text: (i18n.revision, i18n.t("common.show")), value: "tv" } ]
                    textRole: "text"
                    valueRole: "value"
                    onActivated: {
                        genreSelector.currentIndex = 0
                        page.updateSearchMedia()
                        page.applyFilters()
                    }
                }
                Label { text: (i18n.revision, i18n.t("discover.year")); color: Tokens.Theme.textSecondary }
                FilterTextField {
                    id: yearInput
                    enabled: !page.personMode
                    objectName: "discoverYear"
                    Layout.fillWidth: true
                    placeholderText: (i18n.revision, i18n.t("discover.year_placeholder"))
                    color: Tokens.Theme.textPrimary
                    validator: IntValidator { bottom: 1888; top: 2100 }
                }
                Label { text: (i18n.revision, i18n.t("discover.genre")); color: Tokens.Theme.textSecondary }
                FilterComboBox {
                    id: genreSelector
                    enabled: !page.personMode
                    objectName: "discoverGenre"
                    Layout.fillWidth: true
                    model: mediaSelector.currentValue === "movie"
                           ? page.movieGenres : page.tvGenres
                    textRole: "text"
                    valueRole: "value"
                }
                Label { text: (i18n.revision, i18n.t("discover.country")); color: Tokens.Theme.textSecondary }
                FilterComboBox {
                    id: countrySelector
                    enabled: !page.personMode
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
                    enabled: !page.personMode
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
                    enabled: !page.personMode
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
                    text: page.personMode
                        ? "Kişi aramasında Film/Dizi seçimi kullanılır. Yapımlar en yeniden eskiye sıralanır."
                        : "Sıralama: Popülerlik · En az 100 oy"
                    color: Tokens.Theme.textMuted
                    font.pixelSize: Tokens.Theme.textSmall
                    wrapMode: Text.WordWrap
                }
                Item { Layout.fillHeight: true }
                IzlekButton {
                    objectName: "applyDiscoverFilters"
                    Layout.fillWidth: true
                    text: (i18n.revision, i18n.t("common.apply"))
                    enabled: !page.personMode && !controller.busy && minScore.value <= maxScore.value
                    onClicked: page.applyFilters()
                }
                IzlekButton {
                    objectName: "clearDiscoverFilters"
                    Layout.fillWidth: true
                    text: (i18n.revision, i18n.t("common.clear"))
                    variant: "secondary"
                    enabled: !page.personMode && !controller.busy
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
                        Layout.fillWidth: true
                        text: (i18n.revision, i18n.t("page.discover"))
                        color: Tokens.Theme.textPrimary
                        font.pixelSize: Tokens.Theme.textHeading
                        font.weight: Tokens.Theme.weightDemiBold
                        elide: Text.ElideRight
                    }
                    Label {
                        visible: !page.searching && !controller.busy && controller.items.length > 0
                        text: "Sayfa " + controller.page + " / " + controller.totalPages
                        color: Tokens.Theme.textMuted
                    }
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 650 ? 2 : 1
                    SegmentedControl {
                        objectName: "discoverSearchMode"
                        options: ["İçerik", "Yönetmen", "Oyuncu"]
                        currentIndex: ["title", "director", "actor"].indexOf(page.searchMode)
                        onSelected: function(index) {
                            page.searchMode = ["title", "director", "actor"][index]
                            searchDebounce.stop()
                            page.searchModelController.clear()
                            if (searchInput.text.trim().length >= 3) searchDebounce.start()
                            searchInput.forceActiveFocus()
                        }
                    }
                    Components.SearchField {
                        id: searchInput
                        objectName: "dashboardSearch"
                        Layout.fillWidth: true
                        placeholderText: page.personMode ? (page.directorMode ? "Yönetmen" : "Oyuncu") + " adı ara · Ctrl+K"
                            : (mediaSelector.currentValue === "tv" ? "Dizi" : "Film") + " ara · Ctrl+K"
                        onTextChanged: {
                            if (page.restoringPerson) return
                            searchDebounce.stop()
                            page.searchModelController.clear()
                            if (text.trim().length >= 3) searchDebounce.start()
                        }
                        onAccepted: {
                            searchDebounce.stop()
                            page.runSearch()
                        }
                    }
                }
                RowLayout {
                    visible: page.personMode && !!page.searchModelController.selectedPerson.id
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: (page.searchModelController.selectedPerson.name || "") + (page.directorMode ? " · Yönetmen" : " · Oyuncu")
                        color: Tokens.Theme.textPrimary
                        elide: Text.ElideRight
                    }
                    IzlekButton {
                        objectName: "changeDirectorButton"
                        text: (i18n.revision, i18n.t("common.change"))
                        variant: "secondary"
                        onClicked: page.searchModelController.searchPeople(searchInput.text, page.searchMode)
                    }
                }
                SegmentedControl {
                    objectName: "personResultsScope"
                    visible: page.personMode && !!page.searchModelController.selectedPerson.id
                    options: ["Yeni keşifler", "Tüm yapımları"]
                    currentIndex: page.searchModelController.includeSaved ? 1 : 0
                    onSelected: function(index) { page.searchModelController.setIncludeSaved(index === 1) }
                }
                Label {
                    visible: page.searching
                    text: page.searchModelController.selectedPerson.id ? "Arama sonuçları · " + page.displayedItems.length
                          : searchInput.text.trim().length < 3 ? "Aramak için en az 3 karakter yazın."
                          : page.choosingPerson ? "Yapımlarını görmek için bir kişi seç · " + page.searchModelController.people.length
                          : "Arama sonuçları · " + page.displayedItems.length
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Tokens.Theme.textMuted
                }
                Label {
                    visible: !!page.libraryActions.error
                    text: page.libraryActions.error
                    color: Tokens.Theme.danger
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                ColumnLayout {
                    objectName: "discoverForYou"
                    visible: !page.searching && controller.showForYou && (controller.forYou || []).length > 0
                    Layout.fillWidth: true
                    spacing: Tokens.Theme.spaceXs
                    Label {
                        text: (i18n.revision, i18n.t("discover.for_you"))
                        color: Tokens.Theme.textPrimary
                        font.pixelSize: Tokens.Theme.textBody
                        font.weight: Tokens.Theme.weightDemiBold
                    }
                    Label {
                        Layout.fillWidth: true
                        text: (i18n.revision, i18n.t("discover.for_you_help"))
                        color: Tokens.Theme.textMuted
                        font.pixelSize: Tokens.Theme.textSmall
                        wrapMode: Text.WordWrap
                    }
                    HorizontalMediaStrip {
                        objectName: "discoverForYouStrip"
                        Layout.fillWidth: true
                        items: controller.forYou || []
                        onMediaActivated: function(media) {
                            page.mediaSelected(media.mediaType, media.id)
                        }
                    }
                }
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    LoadingState {
                        anchors.centerIn: parent
                        visible: page.resultsBusy
                        count: 4
                        skeletonPosterHeight: 210
                    }
                    EmptyState {
                        anchors.centerIn: parent
                        visible: !page.resultsBusy && !!page.resultsError
                        title: page.searching ? "Arama tamamlanamadı" : "Keşfet yüklenemedi"
                        description: page.resultsError
                        actionText: "Tekrar Dene"
                        onActionRequested: page.searching
                            ? page.runSearch() : page.applyFilters()
                    }
                    EmptyState {
                        anchors.centerIn: parent
                        visible: !page.resultsBusy && !page.resultsError
                                 && page.displayedItems.length === 0
                                 && (!page.choosingPerson || page.searchModelController.people.length === 0)
                                 && (!page.searching || !!page.searchModelController.selectedPerson.id || searchInput.text.trim().length >= 3)
                        title: (i18n.revision, i18n.t("discover.no_results"))
                        description: page.choosingPerson ? "Başka bir kişi adıyla tekrar arayın."
                            : page.personMode ? "Bu görünümde yapım bulunamadı. Tüm yapımları veya Film/Dizi seçimini değiştirebilirsin."
                            : page.searching ? "Kaydettiğin ve izlediğin içerikler gizlenir. Başka bir adla tekrar arayın." : "Filtreleri genişletip tekrar deneyin."
                    }
                    ListView {
                        id: directorResults
                        objectName: "directorSearchResults"
                        anchors.fill: parent
                        visible: page.choosingPerson && !page.resultsBusy && !page.resultsError
                        model: page.searchModelController.people
                        clip: true
                        spacing: Tokens.Theme.spaceSm
                        delegate: ItemDelegate {
                            id: personOption
                            required property var modelData
                            objectName: "directorSearchOption"
                            width: directorResults.width
                            height: Tokens.Theme.controlHeight + Tokens.Theme.spaceMd
                            text: modelData.name
                            Accessible.name: text + " yapımlarını göster"
                            onClicked: page.searchModelController.selectPerson(modelData.id, mediaSelector.currentValue, page.searchMode)
                            contentItem: RowLayout {
                                Label {
                                    Layout.fillWidth: true
                                    text: personOption.text
                                    color: Tokens.Theme.textPrimary
                                    elide: Text.ElideRight
                                }
                                Label { text: (i18n.revision, i18n.t("discover.show_credits")); color: Tokens.Theme.textSecondary }
                            }
                            background: Rectangle {
                                radius: Tokens.Theme.radiusSm
                                color: personOption.hovered ? Tokens.Theme.hoverSurface : Tokens.Theme.surfaceElevated
                                border.color: personOption.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
                            }
                        }
                        ScrollBar.vertical: ScrollBar {}
                    }
                    MediaGrid {
                        id: resultsGrid
                        objectName: "discoverResults"
                        anchors.fill: parent
                        visible: !page.resultsBusy && page.displayedItems.length > 0
                        compact: false
                        items: page.displayedItems
                        quickLibraryController: page.libraryActions
                        dismissController: page.searching ? null : personalController
                        onMediaActivated: function(media) {
                            page.mediaSelected(media.mediaType, media.id)
                        }
                    }
                }
                RowLayout {
                    visible: !page.searching
                    Layout.alignment: Qt.AlignHCenter
                    spacing: Tokens.Theme.spaceSm
                    IzlekButton {
                        objectName: "discoverPrevious"
                        text: (i18n.revision, i18n.t("discover.prev"))
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
                        text: (i18n.revision, i18n.t("discover.next"))
                        variant: "secondary"
                        enabled: !controller.busy && controller.page < controller.totalPages
                        onClicked: controller.goToPage(controller.page + 1)
                    }
                }
            }
        }
    }
}
