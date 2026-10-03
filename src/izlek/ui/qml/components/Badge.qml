import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

Rectangle {
    id: badge
    property string text: ""
    property string tone: "neutral" // neutral, accent, success, warning, danger
    readonly property color toneColor: tone === "accent" ? Tokens.Theme.accent
                                       : tone === "success" ? Tokens.Theme.success
                                       : tone === "warning" ? Tokens.Theme.warning
                                       : tone === "danger" ? Tokens.Theme.danger
                                       : Tokens.Theme.textSecondary
    readonly property color toneSurface: tone === "accent" ? Tokens.Theme.accentSurface
                                         : tone === "success" ? Tokens.Theme.successSurface
                                         : tone === "warning" ? Tokens.Theme.warningSurface
                                         : tone === "danger" ? Tokens.Theme.dangerSurface
                                         : Tokens.Theme.surfaceElevated
    implicitWidth: label.implicitWidth + 2 * Tokens.Theme.spaceSm
    implicitHeight: 25
    radius: Tokens.Theme.radiusSm
    color: toneSurface
    Accessible.name: text

    Label {
        id: label
        anchors.centerIn: parent
        text: badge.text
        color: badge.toneColor
        font.pixelSize: Tokens.Theme.textSmall
        font.weight: Tokens.Theme.weightDemiBold
    }
}
