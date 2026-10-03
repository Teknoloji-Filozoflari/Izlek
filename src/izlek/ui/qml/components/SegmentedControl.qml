import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Rectangle {
    id: control
    property var options: []
    property int currentIndex: -1
    signal selected(int index)
    implicitWidth: segments.implicitWidth + 2 * Tokens.Theme.spaceXs
    implicitHeight: Tokens.Theme.controlHeight
    radius: Tokens.Theme.radiusSm
    color: Tokens.Theme.surface
    border.color: Tokens.Theme.border

    RowLayout {
        id: segments
        anchors.fill: parent
        anchors.margins: Tokens.Theme.spaceXs / 2
        spacing: 2

        Repeater {
            model: control.options
            delegate: Button {
                required property int index
                required property var modelData
                text: String(modelData)
                Layout.fillWidth: true
                implicitHeight: control.height - Tokens.Theme.spaceXs
                implicitWidth: Math.max(78, label.implicitWidth + 2 * Tokens.Theme.spaceMd)
                hoverEnabled: true
                focusPolicy: Qt.StrongFocus
                Accessible.name: text
                onClicked: {
                    control.currentIndex = index
                    control.selected(index)
                }
                contentItem: Label {
                    id: label
                    text: parent.text
                    color: control.currentIndex === index
                           ? Tokens.Theme.textPrimary : Tokens.Theme.textSecondary
                    font.pixelSize: Tokens.Theme.textBody
                    font.weight: control.currentIndex === index
                                 ? Tokens.Theme.weightDemiBold : Tokens.Theme.weightMedium
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: Tokens.Theme.radiusSm
                    color: control.currentIndex === index ? Tokens.Theme.surfaceElevated
                         : parent.hovered ? Tokens.Theme.hoverSurface : "transparent"
                    border.width: parent.activeFocus ? 2 : 0
                    border.color: Tokens.Theme.accent
                }
            }
        }
    }
}
