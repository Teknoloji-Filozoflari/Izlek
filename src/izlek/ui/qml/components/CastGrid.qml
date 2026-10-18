import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Flow {
    id: grid
    property var cast: []
    signal actorActivated(int personId, string name)
    property string photoObjectName: "actorPhoto"
    spacing: Tokens.Theme.spaceMd
    Repeater {
        model: cast
        Button {
            id: actorCard
            objectName: "castActorCard"
            required property var modelData
            width: 128
            height: 240
            padding: Tokens.Theme.spaceSm
            enabled: modelData.id > 0
            hoverEnabled: true
            focusPolicy: Qt.StrongFocus
            Accessible.name: modelData.name + " yapımlarını göster"
            onClicked: grid.actorActivated(modelData.id, modelData.name)
            background: Rectangle {
                color: actorCard.hovered ? Tokens.Theme.surfaceElevated : Tokens.Theme.surface
                radius: Tokens.Theme.radiusMd
                border.color: actorCard.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
                border.width: actorCard.activeFocus ? 2 : 1
            }
            contentItem: ColumnLayout {
                spacing: Tokens.Theme.spaceXs
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 156
                    radius: Tokens.Theme.radiusSm
                    color: Tokens.Theme.surfaceElevated
                    clip: true
                    Image {
                        id: actorPhoto
                        objectName: photoObjectName
                        anchors.fill: parent
                        source: modelData.profilePath ? (modelData.poster || "") : ""
                        asynchronous: true
                        fillMode: Image.PreserveAspectCrop
                        sourceSize.width: 185
                        sourceSize.height: 278
                    }
                    Label {
                        anchors.centerIn: parent
                        visible: actorPhoto.status !== Image.Ready
                        text: "Fotoğraf yok"
                        color: Tokens.Theme.textMuted
                        font.pixelSize: Tokens.Theme.textSmall
                    }
                }
                Label {
                    Layout.fillWidth: true
                    text: modelData.name
                    color: Tokens.Theme.textPrimary
                    font.weight: Tokens.Theme.weightDemiBold
                    maximumLineCount: 2
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                }
                Label {
                    Layout.fillWidth: true
                    text: modelData.character || ""
                    color: Tokens.Theme.textMuted
                    font.pixelSize: Tokens.Theme.textSmall
                    maximumLineCount: 2
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                }
                Item { Layout.fillHeight: true }
            }
            ToolTip.visible: hovered
            ToolTip.text: modelData.name + " · Oynadığı yapımları göster"
        }
    }
}
