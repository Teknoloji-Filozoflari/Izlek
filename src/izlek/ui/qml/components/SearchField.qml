import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

TextField {
    id: field
    implicitHeight: Tokens.Theme.controlHeight + 4
    implicitWidth: 320
    leftPadding: 44
    rightPadding: clearButton.visible ? 46 : Tokens.Theme.spaceMd
    placeholderText: "Film veya dizi ara"
    color: Tokens.Theme.textPrimary
    placeholderTextColor: Tokens.Theme.textMuted
    selectionColor: Tokens.Theme.accentSurface
    selectedTextColor: Tokens.Theme.textPrimary
    font.pixelSize: Tokens.Theme.textBody
    focusPolicy: Qt.StrongFocus
    Accessible.name: "Arama"

    Image {
        source: Qt.resolvedUrl("../../../resources/icons/search.svg")
        anchors.left: parent.left
        anchors.leftMargin: Tokens.Theme.spaceMd
        anchors.verticalCenter: parent.verticalCenter
        sourceSize.width: 20
        sourceSize.height: 20
    }

    IconButton {
        id: clearButton
        objectName: "searchClear"
        visible: field.text.length > 0
        iconSource: Qt.resolvedUrl("../../../resources/icons/close.svg")
        toolTipText: "Aramayı temizle"
        anchors.right: parent.right
        anchors.rightMargin: 2
        anchors.verticalCenter: parent.verticalCenter
        onClicked: {
            field.text = ""
            field.forceActiveFocus()
        }
    }

    background: Rectangle {
        color: Tokens.Theme.surface
        radius: Tokens.Theme.radiusSm
        border.width: field.activeFocus ? 2 : 1
        border.color: field.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
    }
}
