import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property string pageTitle: (i18n.revision, i18n.t("page.lists"))
    property var controller
    readonly property bool filterPopupOpen: mediaPicker.visible
    signal mediaSelected(string kind, int tmdbId)
    color: Tokens.Theme.background

    Component.onCompleted: controller.refresh()
    onVisibleChanged: { if (visible) controller.refresh() }

    RowLayout {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceLg
        spacing: Tokens.Theme.spaceMd

        Rectangle {
            Layout.preferredWidth: Math.min(280, page.width * 0.35)
            Layout.fillHeight: true
            color: Tokens.Theme.surface
            radius: Tokens.Theme.radiusMd
            border.color: Tokens.Theme.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Tokens.Theme.spaceMd
                spacing: Tokens.Theme.spaceSm
                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: page.pageTitle
                        color: Tokens.Theme.textPrimary
                        font.pixelSize: Tokens.Theme.textHeading
                        font.weight: Tokens.Theme.weightDemiBold
                    }
                    Item { Layout.fillWidth: true }
                    IzlekButton {
                        objectName: "createListButton"
                        text: (i18n.revision, i18n.t("lists.new"))
                        enabled: !controller.busy
                        onClicked: page.openNameDialog(false)
                    }
                }
                Label {
                    visible: !page.hasCustomLists()
                    Layout.fillWidth: true
                    text: (i18n.revision, i18n.t("lists.empty"))
