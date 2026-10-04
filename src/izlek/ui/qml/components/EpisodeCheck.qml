import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

CheckBox {
    id: control
    property string episodeName: ""
    implicitWidth: 44
    implicitHeight: 44
    text: ""
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: episodeName + (checked ? " · İzlendi, işareti kaldır" : " · İzlendi olarak işaretle")
    ToolTip.visible: hovered
    ToolTip.text: checked ? "İzlendi işaretini kaldır" : "İzlendi olarak işaretle"
    indicator: Rectangle {
        implicitWidth: 30
        implicitHeight: 30
        x: (control.width - width) / 2
        y: (control.height - height) / 2
        radius: width / 2
        color: control.checked ? Tokens.Theme.statsAccent : "transparent"
        border.width: control.activeFocus ? 2 : 1
        border.color: control.checked || control.activeFocus ? Tokens.Theme.statsAccent
                                                            : control.hovered ? Tokens.Theme.textSecondary : Tokens.Theme.border
        Label {
            anchors.centerIn: parent
            text: control.checked ? "✓" : ""
            color: Tokens.Theme.statsAccentText
            font.pixelSize: Tokens.Theme.textEmpty
            font.weight: Tokens.Theme.weightDemiBold
        }
    }
    contentItem: Item {}
}
