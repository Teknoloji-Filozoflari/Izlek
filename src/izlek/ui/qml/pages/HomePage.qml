import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme" as Tokens

Rectangle {
    id: page
    property string pageTitle: "İstatistikler"
    property var statisticsModelController
    color: Tokens.Theme.background
    function refreshDashboard() {
        statisticsModelController.refresh()
    }
    Component.onCompleted: refreshDashboard()
    onVisibleChanged: { if (visible) refreshDashboard() }
    ScrollView {
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceLg
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: Tokens.Theme.spaceLg
            Label { text: "İstatistikler"; color: Tokens.Theme.textPrimary; font.pixelSize: Tokens.Theme.textHeading; font.weight: Tokens.Theme.weightDemiBold }
            BusyIndicator { visible: statisticsModelController.busy; running: visible }
            Label { visible: !!statisticsModelController.error; text: statisticsModelController.error; color: Tokens.Theme.textSecondary }
            StatisticsPanel {
                objectName: "dashboardStats"
                Layout.fillWidth: true
                stats: statisticsModelController.stats
            }
        }
    }
}
