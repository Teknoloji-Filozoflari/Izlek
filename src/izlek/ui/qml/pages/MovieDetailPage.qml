import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property var controller
    readonly property string pageKind: "movie"
    property string pageTitle: (i18n.revision, i18n.t("page.movie_detail"))
    property int mediaId: 0
    readonly property bool filterPopupOpen: personalReview.filterPopupOpen
    readonly property var providerGroups: controller.detail.providers || ({})
    signal backRequested()
    signal movieSelected(int itemId)
    signal actorSelected(int personId, string name)
    color: Tokens.Theme.background

    ScrollView {
        objectName: "movieDetailScroll"
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Tokens.Theme.spaceLg

            IzlekButton {
                Layout.leftMargin: Tokens.Theme.spaceXl
                Layout.topMargin: Tokens.Theme.spaceLg
                text: (i18n.revision, i18n.t("common.back"))
                variant: "secondary"
                onClicked: page.backRequested()
            }
            BusyIndicator {
                visible: page.controller.busy
                running: visible
                Layout.alignment: Qt.AlignHCenter
            }
            EmptyState {
                visible: !!page.controller.error
                Layout.fillWidth: true
                title: (i18n.revision, i18n.t("detail.movie_load_failed"))
                description: page.controller.error
            }
            ColumnLayout {
                visible: !!page.controller.detail.title
                Layout.fillWidth: true
                spacing: Tokens.Theme.spaceLg

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 300
                    clip: true
                    Image {
                        anchors.fill: parent
                        source: page.controller.detail.backdrop || ""
                        asynchronous: true
                        fillMode: Image.PreserveAspectCrop
                        sourceSize.width: Math.round(width * Screen.devicePixelRatio)
                        sourceSize.height: Math.round(height * Screen.devicePixelRatio)
                    }
                    Rectangle {
                        anchors.fill: parent
                        color: Tokens.Theme.scrim
                    }
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: Tokens.Theme.spaceXl
                        spacing: Tokens.Theme.spaceXl
                        Image {
                            Layout.preferredWidth: 160
                            Layout.preferredHeight: 240
                            source: page.controller.detail.poster || ""
                            asynchronous: true
                            fillMode: Image.PreserveAspectFit
                            sourceSize.width: Math.round(160 * Screen.devicePixelRatio)
                            sourceSize.height: Math.round(240 * Screen.devicePixelRatio)
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Tokens.Theme.spaceSm
                            Label {
                                Layout.fillWidth: true
                                text: page.controller.detail.title || ""
                                color: Tokens.Theme.textPrimary
                                font.pixelSize: Tokens.Theme.textHeading
                                font.weight: Tokens.Theme.weightDemiBold
                                wrapMode: Text.WordWrap
                            }
                            Label {
                                text: (page.controller.detail.year || "Yıl bilinmiyor")
                                      + " · " + (page.controller.detail.runtime
                                                ? page.controller.detail.runtime + " dk" : "Süre yok")
                                color: Tokens.Theme.textPrimary
                                font.pixelSize: Tokens.Theme.textBody
                            }
                            Label {
                                Layout.fillWidth: true
                                text: (page.controller.detail.genres || []).join(" · ")
                                color: Tokens.Theme.textSecondary
                                wrapMode: Text.WordWrap
                            }
                            Label {
                                text: "TMDb: " + (page.controller.detail.score || 0).toFixed(1) + " / 10"
                                color: Tokens.Theme.accent
                                font.pixelSize: Tokens.Theme.textBody
                            }
                            Label {
                                objectName: "movieTmdbSourceLabel"
                                text: (i18n.revision, i18n.t("detail.movie_attribution"))
                                color: Tokens.Theme.textSecondary
                                font.pixelSize: Tokens.Theme.textSmall
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: Tokens.Theme.spaceXl
                    Layout.rightMargin: Tokens.Theme.spaceXl
                    spacing: Tokens.Theme.spaceMd
                    IzlekButton {
                        objectName: "addMovieToLibrary"
                        visible: !page.controller.detail.status
                        enabled: !page.controller.saving
                        text: (i18n.revision, i18n.t("detail.add_library"))
                        onClicked: page.controller.setStatus("PLANNED")
                    }
                    IzlekButton {
                        objectName: "movieWatched"
                        text: page.controller.detail.status === "WATCHED"
                              ? "Yeniden izledim"
                              : (i18n.revision, i18n.t("status.mark_watched"))
