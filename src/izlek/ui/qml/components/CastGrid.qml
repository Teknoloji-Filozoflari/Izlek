import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Flow {
    property var cast: []
    property string photoObjectName: "actorPhoto"
    spacing: Tokens.Theme.spaceMd
    Repeater {
        model: cast
        Rectangle {
            required property var modelData
            width: 128
            height: 240
            color: Tokens.Theme.surface
            radius: Tokens.Theme.radiusMd
            border.color: Tokens.Theme.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Tokens.Theme.spaceSm
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
        }
    }
}
