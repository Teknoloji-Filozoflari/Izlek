import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

ColumnLayout {
    id: section
    property var groups: ({})
    property string providerLink: ""
    signal providerLinkRequested()
    Layout.fillWidth: true
    spacing: Tokens.Theme.spaceSm

    SectionHeader { title: "Nerede İzlenir"; Layout.fillWidth: true }
    Repeater {
        model: [
            { key: "Abonelik", label: "Abonelik" },
            { key: "Kiralama", label: "Kiralama" },
            { key: "Satın Alma", label: "Satın Alma" }
        ]
        RowLayout {
            required property var modelData
            visible: (section.groups[modelData.key] || []).length > 0
            Layout.fillWidth: true
            spacing: Tokens.Theme.spaceSm
            Label {
                text: modelData.label + ":"
                color: Tokens.Theme.textSecondary
                Layout.preferredWidth: 92
            }
            Flow {
                Layout.fillWidth: true
                spacing: Tokens.Theme.spaceXs
                Repeater {
                    model: section.groups[modelData.key] || []
                    delegate: Rectangle {
                        width: providerName.implicitWidth + 2 * Tokens.Theme.spaceSm
                        height: 30
                        radius: Tokens.Theme.radiusSm
                        color: Tokens.Theme.surfaceElevated
                        border.color: Tokens.Theme.border
                        Label {
                            id: providerName
                            anchors.centerIn: parent
                            text: modelData
                            color: Tokens.Theme.textPrimary
                            font.pixelSize: Tokens.Theme.textSmall
                        }
                    }
                }
            }
        }
    }
    EmptyState {
        visible: !section.hasProviders()
        Layout.fillWidth: true
        implicitHeight: 92
        title: "Türkiye'de sağlayıcı bulunamadı"
        description: "Bu içerik için kayıtlı izleme seçeneği yok."
    }
    Label {
        Layout.fillWidth: true
        text: "İzleme seçenekleri JustWatch tarafından sağlanır · Türkiye"
        color: Tokens.Theme.textMuted
        font.pixelSize: Tokens.Theme.textSmall
        wrapMode: Text.WordWrap
    }
    IzlekButton {
        objectName: "providerLinkButton"
        visible: section.providerLink.length > 0
        text: "TMDb'de izleme seçenekleri"
        variant: "secondary"
        onClicked: section.providerLinkRequested()
    }

    function hasProviders() {
        return ["Abonelik", "Kiralama", "Satın Alma"].some(function(key) {
            return (section.groups[key] || []).length > 0
        })
    }
}
