import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"
import "theme" as Tokens

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    title: "İzlek"
    width: 1280
    height: 800
    minimumWidth: 800
    minimumHeight: 600
    visible: false
    color: Tokens.Theme.background

    property int currentIndex: 0
    readonly property bool compactSidebar: width < 1060
    readonly property var pageComponents: [
        discoverPage, moviesPage, showsPage, listsPage, homePage, settingsPage
    ]

    function cancelSectionTasks(index) {
        if (index === 0)
            discoverController.cancelPending()
        else if (index === 1)
            movieLibraryController.cancelPending()
        else if (index === 2) {
            tvLibraryController.cancelPending()
            continueController.cancelPending()
        }
    }

    function isMovieDetail(item) {
        return item && item.pageKind === "movie"
    }

    function isTvDetail(item) {
        return item && item.pageKind === "tv"
    }

    function navigate(index) {
        if (!tokenController.hasToken || index < 0
                || index >= pageComponents.length
                || (index === currentIndex && contentStack.depth === 1))
            return
        cancelSectionTasks(currentIndex)
        if (isMovieDetail(contentStack.currentItem))
            movieController.cancelPending()
        else if (isTvDetail(contentStack.currentItem))
            tvController.cancelPending()
        currentIndex = index
        contentStack.replace(null, pageComponents[index], StackView.Immediate)
    }

    function openMediaDetail(kind, itemId) {
        if (kind !== "movie" && kind !== "tv")
            return
        if (contentStack.currentItem.mediaId === itemId
                && ((kind === "movie" && isMovieDetail(contentStack.currentItem))
                    || (kind === "tv" && isTvDetail(contentStack.currentItem))))
            return
        globalSearch.close()
        if (isMovieDetail(contentStack.currentItem))
            movieController.cancelPending()
        else if (isTvDetail(contentStack.currentItem))
            tvController.cancelPending()
        if (!isMovieDetail(contentStack.currentItem) && !isTvDetail(contentStack.currentItem))
            cancelSectionTasks(currentIndex)
        if (kind === "movie") {
            contentStack.push(movieDetailPage, { mediaId: itemId }, StackView.Immediate)
            movieController.loadMovie(itemId)
        } else if (kind === "tv") {
            contentStack.push(tvDetailPage, { mediaId: itemId }, StackView.Immediate)
            tvController.loadTv(itemId)
        }
    }

    function openActor(personId, name, kind) {
        window.navigate(0)
        contentStack.currentItem.showActor(personId, name, kind)
    }

    function goBack() {
        if (globalSearch.visible) {
            globalSearch.close()
        } else if (contentStack.depth > 1) {
            if (isMovieDetail(contentStack.currentItem))
                movieController.cancelPending()
            else if (isTvDetail(contentStack.currentItem))
                tvController.cancelPending()
            contentStack.pop(StackView.Immediate)
            if (isMovieDetail(contentStack.currentItem))
                movieController.loadMovie(contentStack.currentItem.mediaId)
            else if (isTvDetail(contentStack.currentItem))
                tvController.loadTv(contentStack.currentItem.mediaId)
        }
    }

    Shortcut {
        sequence: "Ctrl+K"
        context: Qt.ApplicationShortcut
        enabled: tokenController.hasToken
        onActivated: {
            if (currentIndex === 0 && contentStack.depth === 1)
                contentStack.currentItem.focusSearch()
            else globalSearch.open()
        }
    }

    Shortcut { sequence: "Ctrl+1"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(0) }
    Shortcut { sequence: "Ctrl+2"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(1) }
    Shortcut { sequence: "Ctrl+3"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(2) }
    Shortcut { sequence: "Ctrl+4"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(3) }
    Shortcut { sequence: "Ctrl+5"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(4) }
    Shortcut { sequence: "Ctrl+,"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(5) }
    Shortcut {
        sequence: "Escape"
        context: Qt.ApplicationShortcut
        enabled: tokenController.hasToken && (!contentStack.currentItem
                 || contentStack.currentItem.filterPopupOpen !== true)
        onActivated: window.goBack()
    }

    OnboardingPage {
        objectName: "onboardingPage"
        anchors.fill: parent
        visible: !tokenController.hasToken
        controller: tokenController
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0
        visible: tokenController.hasToken

        Rectangle {
            id: sidebar
            objectName: "sidebar"
            Layout.preferredWidth: window.compactSidebar
                                   ? Tokens.Theme.sidebarCompact
                                   : Tokens.Theme.sidebarExpanded
            Layout.fillHeight: true
            color: Tokens.Theme.surface
            border.color: Tokens.Theme.border
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: Tokens.Theme.spaceSm
                anchors.rightMargin: Tokens.Theme.spaceSm
                anchors.topMargin: Tokens.Theme.spaceLg
                anchors.bottomMargin: Tokens.Theme.spaceLg
                spacing: Tokens.Theme.spaceXs

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 54
                    Layout.bottomMargin: Tokens.Theme.spaceLg
                    spacing: Tokens.Theme.spaceSm

                    Image {
                        source: "../../resources/icons/izlek.svg"
                        sourceSize.width: 38
                        sourceSize.height: 38
                        Layout.preferredWidth: 38
                        Layout.preferredHeight: 38
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Label {
                        visible: !window.compactSidebar
                        text: (i18n.revision, i18n.t("app.name"))
                        color: Tokens.Theme.textPrimary
                        font.pixelSize: Tokens.Theme.textBrand
                        font.weight: Tokens.Theme.weightDemiBold
                        Layout.fillWidth: true
                    }
                }

                NavItem {
                    objectName: "navHome"
                    Layout.fillWidth: true
                    label: (i18n.revision, i18n.t("nav.home"))
                    iconSource: Qt.resolvedUrl("../../resources/icons/home.svg")
                    selected: window.currentIndex === 0
                    compact: window.compactSidebar
                    onActivated: window.navigate(0)
                }
                NavItem {
                    objectName: "navMovies"
                    Layout.fillWidth: true
                    label: (i18n.revision, i18n.t("nav.movies"))
                    iconSource: Qt.resolvedUrl("../../resources/icons/movie.svg")
                    selected: window.currentIndex === 1
                    compact: window.compactSidebar
                    onActivated: window.navigate(1)
                }
                NavItem {
                    objectName: "navShows"
                    Layout.fillWidth: true
                    label: (i18n.revision, i18n.t("nav.shows"))
                    iconSource: Qt.resolvedUrl("../../resources/icons/tv.svg")
                    selected: window.currentIndex === 2
                    compact: window.compactSidebar
                    onActivated: window.navigate(2)
                }
                NavItem {
                    objectName: "navLists"
                    Layout.fillWidth: true
                    label: (i18n.revision, i18n.t("nav.lists"))
                    iconSource: Qt.resolvedUrl("../../resources/icons/list.svg")
                    selected: window.currentIndex === 3
                    compact: window.compactSidebar
                    onActivated: window.navigate(3)
                }
                NavItem {
                    objectName: "navStatistics"
                    Layout.fillWidth: true
                    label: (i18n.revision, i18n.t("nav.statistics"))
                    iconSource: Qt.resolvedUrl("../../resources/icons/statistics.svg")
                    selected: window.currentIndex === 4
                    compact: window.compactSidebar
                    onActivated: window.navigate(4)
                }

                Item { Layout.fillHeight: true }

                NavItem {
                    objectName: "navSettings"
                    Layout.fillWidth: true
                    label: (i18n.revision, i18n.t("nav.settings"))
                    iconSource: Qt.resolvedUrl("../../resources/icons/settings.svg")
                    selected: window.currentIndex === 5
                    compact: window.compactSidebar
                    onActivated: window.navigate(5)
                }
            }
        }

        StackView {
            id: contentStack
            objectName: "contentStack"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            initialItem: discoverPage
        }
    }

    Component {
        id: homePage
        HomePage {
            statisticsModelController: statisticsController
        }
    }
    Component {
        id: moviesPage
        MoviesPage {
            controller: movieLibraryController
            onMovieSelected: function(itemId) {
                window.openMediaDetail("movie", itemId)
            }
        }
    }
    Component {
        id: showsPage
        ShowsPage {
            controller: tvLibraryController
            continueModelController: continueController
            onTvSelected: function(itemId) {
                window.openMediaDetail("tv", itemId)
            }
        }
    }
    Component {
        id: listsPage
        ListsPage {
            controller: customListsController
            onMediaSelected: function(kind, itemId) {
                window.openMediaDetail(kind, itemId)
            }
        }
    }
    Component {
        id: discoverPage
        DiscoverPage {
            controller: discoverController
            searchModelController: searchController
            onSearchRequested: globalSearch.open()
            onMediaSelected: function(kind, itemId) {
                window.openMediaDetail(kind, itemId)
            }
        }
    }
    Component {
        id: settingsPage
        SettingsPage {
            controller: tokenController
            transferModelController: transferController
        }
    }
    Component {
        id: detailPage
        MediaDetailPage {
            controller: searchController
            onBackRequested: window.goBack()
        }
    }
    Component {
        id: movieDetailPage
        MovieDetailPage {
            controller: movieController
            onActorSelected: function(personId, name) { window.openActor(personId, name, "movie") }
            onBackRequested: window.goBack()
            onMovieSelected: function(itemId) {
                window.openMediaDetail("movie", itemId)
            }
        }
    }
    Component {
        id: tvDetailPage
        TvDetailPage {
            controller: tvController
            onActorSelected: function(personId, name) { window.openActor(personId, name, "tv") }
            onBackRequested: window.goBack()
            onTvSelected: function(itemId) { window.openMediaDetail("tv", itemId) }
        }
    }

    GlobalSearch {
        id: globalSearch
        objectName: "globalSearch"
        controller: searchController
        onResultActivated: function(kind, itemId) {
            window.openMediaDetail(kind, itemId)
        }
    }

    Toast {
        id: tokenToast
        parent: Overlay.overlay
    }
    Connections {
        target: tokenController
        function onTokenSaved() {
            Qt.callLater(function() {
                if (window.currentIndex === 0
                        && contentStack.currentItem.pageTitle === "Ana Sayfa")
                    contentStack.currentItem.applyFilters()
            })
        }
        function onHasTokenChanged() {
            if (tokenController.hasToken)
                tokenToast.show(tokenController.feedback, tokenController.feedbackKind)
        }
    }
}
