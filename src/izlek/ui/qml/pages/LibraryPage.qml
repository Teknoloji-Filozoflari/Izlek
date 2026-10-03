import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property string kind: "movie"
    property string pageTitle: kind === "movie" ? "Filmler" : "Diziler"
    property var controller
    readonly property string emptyTitle:
        controller.status === "PLANNED" ? "İzlenecek " + mediaNoun + " yok"
        : controller.status === "WATCHING" ? "İzleniyor " + mediaNoun + " yok"
        : "İzlenen " + mediaNoun + " yok"
    readonly property string mediaNoun: kind === "movie" ? "film" : "dizi"
    signal mediaSelected(int tmdbId)
    color: Tokens.Theme.background

    Component.onCompleted: controller.refresh()
    onVisibleChanged: {
        if (visible) controller.refresh()
    }

    Column {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceLg
        spacing: Tokens.Theme.spaceSm

        RowLayout {
            width: parent.width
            height: 40
            Label {
                text: page.pageTitle
                color: Tokens.Theme.textPrimary
                font.pixelSize: Tokens.Theme.textHeading
                font.weight: Tokens.Theme.weightDemiBold
            }
            Item { Layout.fillWidth: true }
            Label {
                text: (controller.stats.total || 0) + " " + page.mediaNoun
                color: Tokens.Theme.textSecondary
                font.pixelSize: Tokens.Theme.textBody
            }
        }

        RowLayout {
            width: parent.width
            height: Tokens.Theme.controlHeight
            spacing: Tokens.Theme.spaceMd
            SegmentedControl {
                id: statusTabs
                objectName: page.kind === "movie" ? "movieStatusTabs" : "tvStatusTabs"
                options: ["İzlenecek", "İzleniyor", "İzlendi"]
                currentIndex: 0
                onSelected: function(index) {
                    controller.setStatus(["PLANNED", "WATCHING", "WATCHED"][index])
                }
            }
            Item { Layout.fillWidth: true }
            Label {
                text: "Sırala"
                color: Tokens.Theme.textSecondary
            }
            ComboBox {
                id: sortBox
                objectName: page.kind === "movie" ? "movieSort" : "tvSort"
                Layout.preferredWidth: 168
                Layout.preferredHeight: Tokens.Theme.controlHeight
                model: [
                    { text: "Son Eklenen", value: "recent" },
                    { text: "Başlık", value: "title" },
                    { text: "Yıl", value: "year" },
                    { text: "TMDb Puanı", value: "score" }
                ]
                textRole: "text"
                valueRole: "value"
                onActivated: controller.setSort(currentValue)
                contentItem: Label {
                    text: sortBox.displayText
                    color: Tokens.Theme.textPrimary
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: Tokens.Theme.spaceSm
                }
                background: Rectangle {
                    color: Tokens.Theme.surface
                    radius: Tokens.Theme.radiusSm
                    border.color: sortBox.activeFocus ? Tokens.Theme.accent
                                                      : Tokens.Theme.border
                    border.width: sortBox.activeFocus ? 2 : 1
                }
                delegate: ItemDelegate {
                    width: sortBox.width
                    text: modelData.text
                    contentItem: Label {
                        text: parent.text
                        color: Tokens.Theme.textPrimary
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: parent.hovered ? Tokens.Theme.hoverSurface
                                              : Tokens.Theme.surfaceElevated
                    }
                }
                popup: Popup {
                    y: sortBox.height
                    width: sortBox.width
                    padding: 0
                    contentItem: ListView {
                        implicitHeight: contentHeight
                        model: sortBox.popup.visible ? sortBox.delegateModel : null
                    }
                    background: Rectangle {
                        color: Tokens.Theme.surfaceElevated
                        border.color: Tokens.Theme.border
                        radius: Tokens.Theme.radiusSm
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            readonly property int rowCount: Math.max(
                1, Math.ceil(controller.items.length / Math.max(1, movieGrid.columns)))
            height: Math.min(
                rowCount * movieGrid.cellHeight + 2 * Tokens.Theme.spaceSm,
                Math.max(160, page.height - 410))
            color: Tokens.Theme.surface
            radius: Tokens.Theme.radiusLg
            border.color: Tokens.Theme.border

            LibraryPosterGrid {
                id: movieGrid
                objectName: page.kind === "movie" ? "movieLibraryGrid"
                                                 : "tvLibraryGrid"
                anchors.fill: parent
                anchors.margins: Tokens.Theme.spaceSm
                visible: controller.items.length > 0
                items: controller.items
                onPosterRequested: function(tmdbId) { controller.requestPoster(tmdbId) }
                onMediaActivated: function(tmdbId) { page.mediaSelected(tmdbId) }
                onFavoriteToggled: function(tmdbId, favorite) {
                    controller.setFavorite(tmdbId, favorite)
                }
            }
            LoadingState {
                anchors.centerIn: parent
                width: parent.width - 2 * Tokens.Theme.spaceMd
                visible: controller.busy
                count: Math.max(2, Math.floor(width / (Tokens.Theme.cardWidth
                                                       + Tokens.Theme.gridGap)))
                skeletonPosterHeight: 210
            }
            EmptyState {
                objectName: page.kind === "movie" ? "movieLibraryEmpty"
                                                 : "tvLibraryEmpty"
                anchors.centerIn: parent
                width: parent.width - 2 * Tokens.Theme.spaceMd
                height: Math.min(206, parent.height)
                visible: !controller.busy && controller.items.length === 0
                title: controller.error || page.emptyTitle
                description: controller.error ? "Lütfen tekrar deneyin."
                    : (page.kind === "movie" ? "Film" : "Dizi")
                      + " arayıp kütüphanene eklediğinde burada görünecek."
            }
        }

        ColumnLayout {
            width: parent.width
            height: 142
            spacing: Tokens.Theme.spaceXs
            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: page.kind === "movie" ? "Favori Filmler" : "Favori Diziler"
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textEmpty
                    font.weight: Tokens.Theme.weightDemiBold
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: controller.favorites.length + " " + page.mediaNoun
                    color: Tokens.Theme.textMuted
                }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Tokens.Theme.surface
                radius: Tokens.Theme.radiusMd
                border.color: Tokens.Theme.border
                Label {
                    anchors.centerIn: parent
                    visible: controller.favorites.length === 0
                    text: "Favori " + page.mediaNoun + " yok"
                    color: Tokens.Theme.textSecondary
                }
                ListView {
                    id: favoritesStrip
                    objectName: page.kind === "movie" ? "favoriteMoviesStrip"
                                                     : "favoriteShowsStrip"
                    anchors.fill: parent
                    anchors.margins: Tokens.Theme.spaceXs
                    orientation: ListView.Horizontal
                    spacing: Tokens.Theme.spaceSm
                    clip: true
                    model: controller.favorites
                    delegate: ItemDelegate {
                        required property var modelData
                        width: 198
                        height: favoritesStrip.height
                        Component.onCompleted: Qt.callLater(function() {
                            controller.requestPoster(modelData.tmdb_id)
                        })
                        onClicked: page.mediaSelected(modelData.tmdb_id)
                        background: Rectangle {
                            color: parent.hovered ? Tokens.Theme.hoverSurface
                                                  : Tokens.Theme.surfaceElevated
                            radius: Tokens.Theme.radiusSm
                        }
                        contentItem: RowLayout {
                            spacing: Tokens.Theme.spaceSm
                            Image {
                                Layout.preferredWidth: 57
                                Layout.fillHeight: true
                                source: modelData.poster || ""
                                fillMode: Image.PreserveAspectCrop
                                sourceSize.width: Math.round(57 * Screen.devicePixelRatio)
                                sourceSize.height: Math.round(height * Screen.devicePixelRatio)
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.title || ""
                                    color: Tokens.Theme.textPrimary
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                                Label {
                                    text: modelData.year || ""
                                    color: Tokens.Theme.textMuted
                                    font.pixelSize: Tokens.Theme.textSmall
                                }
                            }
                            FavoriteButton {
                                Layout.preferredWidth: Tokens.Theme.controlHeight
                                checked: !!modelData.favorite
                                onToggledFavorite: function(value) {
                                    controller.setFavorite(modelData.tmdb_id, value)
                                }
                            }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            objectName: page.kind === "movie" ? "movieStats" : "tvStats"
            width: parent.width
            height: 101
            spacing: Tokens.Theme.spaceXs
            Label {
                text: page.kind === "movie" ? "Film İstatistikleri"
                                             : "Dizi İstatistikleri"
                color: Tokens.Theme.textPrimary
                font.pixelSize: Tokens.Theme.textEmpty
                font.weight: Tokens.Theme.weightDemiBold
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Tokens.Theme.surface
                radius: Tokens.Theme.radiusMd
                border.color: Tokens.Theme.border
                RowLayout {
                    id: statsRow
                    anchors.fill: parent
                    anchors.margins: Tokens.Theme.spaceSm
                    spacing: Tokens.Theme.spaceSm
                    Repeater {
                        model: [
                            { label: "Toplam", count: controller.stats.total || 0 },
                            { label: "İzlenecek", count: controller.stats.planned || 0 },
                            { label: "İzleniyor", count: controller.stats.watching || 0 },
                            { label: "İzlendi", count: controller.stats.watched || 0 }
                        ]
                        ColumnLayout {
                            parent: statsRow
                            Layout.fillWidth: true
                            spacing: 0
                            Label {
                                text: modelData.count
                                color: Tokens.Theme.textPrimary
                                font.pixelSize: Tokens.Theme.textEmpty
                                font.weight: Tokens.Theme.weightDemiBold
                            }
                            Label {
                                text: modelData.label
                                color: Tokens.Theme.textSecondary
                                font.pixelSize: Tokens.Theme.textSmall
                            }
                        }
                    }
                }
            }
        }
    }
}
