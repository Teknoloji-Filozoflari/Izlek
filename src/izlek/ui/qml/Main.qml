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
        homePage, moviesPage, showsPage, listsPage, discoverPage, settingsPage
    ]

    function cancelSectionTasks(index) {
        if (index === 0)
            continueController.cancelPending()
        else if (index === 1)
            movieLibraryController.cancelPending()
        else if (index === 2)
            tvLibraryController.cancelPending()
        else if (index === 4)
            discoverController.cancelPending()
    }

    function navigate(index) {
        if (!tokenController.hasToken || index < 0
                || index >= pageComponents.length
                || (index === currentIndex && contentStack.depth === 1))
            return
        cancelSectionTasks(currentIndex)
        if (contentStack.currentItem.pageTitle === "Film Detayı")
            movieController.cancelPending()
        else if (contentStack.currentItem.pageTitle === "Dizi Detayı")
            tvController.cancelPending()
        currentIndex = index
        contentStack.replace(pageComponents[index])
    }

    function openMediaDetail(kind, itemId) {
        globalSearch.close()
        if (contentStack.currentItem.pageTitle !== "Film Detayı"
                && contentStack.currentItem.pageTitle !== "Dizi Detayı")
            cancelSectionTasks(currentIndex)
        if (kind === "movie") {
            if (contentStack.currentItem.pageTitle === "Film Detayı")
                contentStack.replace(movieDetailPage)
            else
                contentStack.push(movieDetailPage)
            movieController.loadMovie(itemId)
        } else if (kind === "tv") {
            if (contentStack.currentItem.pageTitle === "Dizi Detayı")
                contentStack.replace(tvDetailPage)
            else
                contentStack.push(tvDetailPage)
            tvController.loadTv(itemId)
        }
    }

    function goBack() {
        if (globalSearch.visible) {
            globalSearch.close()
        } else if (contentStack.depth > 1) {
            if (contentStack.currentItem.pageTitle === "Film Detayı")
                movieController.cancelPending()
            else if (contentStack.currentItem.pageTitle === "Dizi Detayı")
                tvController.cancelPending()
            contentStack.pop()
        }
    }

    Shortcut {
        sequence: "Ctrl+K"
        context: Qt.ApplicationShortcut
        enabled: tokenController.hasToken
        onActivated: globalSearch.open()
    }

    Shortcut { sequence: "Ctrl+1"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(0) }
    Shortcut { sequence: "Ctrl+2"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(1) }
    Shortcut { sequence: "Ctrl+3"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(2) }
    Shortcut { sequence: "Ctrl+4"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(3) }
    Shortcut { sequence: "Ctrl+5"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(4) }
    Shortcut { sequence: "Ctrl+,"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.navigate(5) }
    Shortcut { sequence: "Escape"; context: Qt.ApplicationShortcut; enabled: tokenController.hasToken; onActivated: window.goBack() }

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
                        text: "İzlek"
                        color: Tokens.Theme.textPrimary
                        font.pixelSize: Tokens.Theme.textBrand
                        font.weight: Tokens.Theme.weightDemiBold
                        Layout.fillWidth: true
                    }
                }

                NavItem {
                    objectName: "navHome"
                    Layout.fillWidth: true
                    label: "Ana Sayfa"
                    iconSource: Qt.resolvedUrl("../../resources/icons/home.svg")
                    selected: window.currentIndex === 0
                    compact: window.compactSidebar
                    onActivated: window.navigate(0)
                }
                NavItem {
                    objectName: "navMovies"
                    Layout.fillWidth: true
                    label: "Filmler"
                    iconSource: Qt.resolvedUrl("../../resources/icons/movie.svg")
                    selected: window.currentIndex === 1
                    compact: window.compactSidebar
                    onActivated: window.navigate(1)
                }
                NavItem {
                    objectName: "navShows"
                    Layout.fillWidth: true
                    label: "Diziler"
                    iconSource: Qt.resolvedUrl("../../resources/icons/tv.svg")
                    selected: window.currentIndex === 2
                    compact: window.compactSidebar
                    onActivated: window.navigate(2)
                }
                NavItem {
                    objectName: "navLists"
                    Layout.fillWidth: true
                    label: "Listeler"
                    iconSource: Qt.resolvedUrl("../../resources/icons/list.svg")
                    selected: window.currentIndex === 3
                    compact: window.compactSidebar
                    onActivated: window.navigate(3)
                }
                NavItem {
                    objectName: "navDiscover"
                    Layout.fillWidth: true
                    label: "Keşfet"
                    iconSource: Qt.resolvedUrl("../../resources/icons/discover.svg")
                    selected: window.currentIndex === 4
                    compact: window.compactSidebar
                    onActivated: window.navigate(4)
                }

                Item { Layout.fillHeight: true }

                NavItem {
                    objectName: "navSettings"
                    Layout.fillWidth: true
                    label: "Ayarlar"
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
            initialItem: homePage
        }
    }

    Component {
        id: homePage
        HomePage {
            controller: continueController
            favoritesModelController: favoritesController
            movieLibraryModelController: movieLibraryController
            tvLibraryModelController: tvLibraryController
            statisticsModelController: statisticsController
            onTvSelected: function(itemId) { window.openMediaDetail("tv", itemId) }
            onFavoriteSelected: function(kind, itemId) {
                window.openMediaDetail(kind, itemId)
            }
            onSearchRequested: globalSearch.open()
            onMoviesRequested: window.navigate(1)
            onShowsRequested: window.navigate(2)
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
            onBackRequested: contentStack.pop()
        }
    }
    Component {
        id: movieDetailPage
        MovieDetailPage {
            controller: movieController
            onBackRequested: contentStack.pop()
            onMovieSelected: function(itemId) {
                movieController.loadMovie(itemId)
            }
        }
    }
    Component {
        id: tvDetailPage
        TvDetailPage {
            controller: tvController
            onBackRequested: contentStack.pop()
            onTvSelected: function(itemId) { tvController.loadTv(itemId) }
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
        function onHasTokenChanged() {
            if (tokenController.hasToken)
                tokenToast.show(tokenController.feedback, tokenController.feedbackKind)
        }
    }
}
