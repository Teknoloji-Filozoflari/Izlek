import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Button {
    id: control
    property string label: ""
    property url iconSource
    property bool selected: false
    property bool compact: false
    readonly property bool iconReady: navIcon.status === Image.Ready
    signal activated()

    text: label
    implicitHeight: 48
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: label
    ToolTip.visible: control.compact && control.hovered
    ToolTip.text: control.label
    ToolTip.delay: 500
    onClicked: activated()

    contentItem: RowLayout {
        spacing: Tokens.Theme.spaceMd
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: control.compact ? 0 : Tokens.Theme.spaceMd
        anchors.rightMargin: Tokens.Theme.spaceSm

        Image {
            id: navIcon
            source: control.iconSource
            sourceSize.width: 22
            sourceSize.height: 22
            Layout.preferredWidth: 22
            Layout.preferredHeight: 22
            Layout.alignment: control.compact ? Qt.AlignHCenter : Qt.AlignVCenter
            opacity: control.selected ? 1 : 0.78
            fillMode: Image.PreserveAspectFit
        }

        Label {
            visible: !control.compact
            text: control.label
            color: control.selected ? Tokens.Theme.textPrimary : Tokens.Theme.textSecondary
            font.pixelSize: Tokens.Theme.textBody
            font.weight: control.selected ? Tokens.Theme.weightDemiBold
                                          : Tokens.Theme.weightMedium
            Layout.fillWidth: true
            elide: Text.ElideRight
        }
    }

    background: Rectangle {
        radius: Tokens.Theme.radiusSm
        color: control.selected ? Tokens.Theme.surfaceElevated
              : control.hovered ? Tokens.Theme.surface : "transparent"
        border.width: control.activeFocus ? 2 : 0
        border.color: Tokens.Theme.accent
        Behavior on color {
            ColorAnimation { duration: Tokens.Theme.animationFast }
        }
    }
}
