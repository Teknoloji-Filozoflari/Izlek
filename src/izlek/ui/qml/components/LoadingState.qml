import QtQuick
import QtQuick.Layouts
import "../theme" as Tokens

Item {
    id: loadingState
    property int count: 4
    property int skeletonPosterHeight: Tokens.Theme.posterHeight
    implicitHeight: skeletonPosterHeight + 46

    RowLayout {
        anchors.fill: parent
        spacing: Tokens.Theme.gridGap
        Repeater {
            model: Math.max(1, loadingState.count)
            delegate: ColumnLayout {
                Layout.preferredWidth: Tokens.Theme.cardWidth
                Layout.alignment: Qt.AlignTop
                spacing: Tokens.Theme.spaceSm
                Skeleton {
                    Layout.fillWidth: true
                    Layout.preferredHeight: loadingState.skeletonPosterHeight
                    radius: Tokens.Theme.radiusMd
                }
                Skeleton { Layout.fillWidth: true; Layout.preferredHeight: 13 }
                Skeleton { Layout.preferredWidth: 66; Layout.preferredHeight: 11 }
            }
        }
        Item { Layout.fillWidth: true }
    }
}
