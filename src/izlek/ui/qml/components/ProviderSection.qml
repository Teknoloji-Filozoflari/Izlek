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
    spacing: Tokens.Theme.spaceMd

    readonly property var groupOrder: [
        { key: "Abonelik", labelKey: "provider.group_subscription", hintKey: "provider.hint_subscription" },
        { key: "Ücretsiz", labelKey: "provider.group_free", hintKey: "provider.hint_free" },
        { key: "Reklamlı", labelKey: "provider.group_ads", hintKey: "provider.hint_ads" },
        { key: "Kiralama", labelKey: "provider.group_rent", hintKey: "provider.hint_rent" },
        { key: "Satın Alma", labelKey: "provider.group_buy", hintKey: "provider.hint_buy" }
    ]

    SectionHeader { title: (i18n.revision, i18n.t("provider.title")); Layout.fillWidth: true }
    Label {
        Layout.fillWidth: true
        text: (i18n.revision, i18n.t("provider.help"))
        color: Tokens.Theme.textMuted
        font.pixelSize: Tokens.Theme.textSmall
        wrapMode: Text.WordWrap
    }

    Repeater {
        model: section.groupOrder
        delegate: ColumnLayout {
            id: groupBlock
            required property var modelData
            readonly property var names: section.groups[modelData.key] || []
            visible: names.length > 0
            Layout.fillWidth: true
            spacing: Tokens.Theme.spaceXs

            RowLayout {
                Layout.fillWidth: true
                spacing: Tokens.Theme.spaceSm
                Label {
                    text: (i18n.revision, i18n.t(modelData.labelKey))
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textBody
                    font.weight: Tokens.Theme.weightDemiBold
                }
                Label {
                    Layout.fillWidth: true
                    text: (i18n.revision, i18n.t(modelData.hintKey))
                    color: Tokens.Theme.textMuted
                    font.pixelSize: Tokens.Theme.textSmall
                    elide: Text.ElideRight
                }
            }
            Flow {
                Layout.fillWidth: true
                spacing: Tokens.Theme.spaceXs
                Repeater {
                    model: groupBlock.names
                    delegate: Rectangle {
                        required property var modelData
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
        title: (i18n.revision, i18n.t("provider.empty"))
        description: (i18n.revision, i18n.t("provider.empty_help"))
    }
    Label {
        Layout.fillWidth: true
        text: (i18n.revision, i18n.t("provider.attribution"))
        color: Tokens.Theme.textMuted
        font.pixelSize: Tokens.Theme.textSmall
        wrapMode: Text.WordWrap
    }
    IzlekButton {
        objectName: "providerLinkButton"
        visible: section.providerLink.length > 0
        text: (i18n.revision, i18n.t("provider.tmdb_link"))
        variant: "secondary"
        onClicked: section.providerLinkRequested()
    }

    function hasProviders() {
        return section.groupOrder.some(function(item) {
            return (section.groups[item.key] || []).length > 0
        })
    }
}
