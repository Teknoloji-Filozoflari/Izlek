import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

Button {
    id: control
    property string variant: "primary" // primary, secondary, ghost, danger
    property url iconSource
    readonly property color fillColor: variant === "primary" ? Tokens.Theme.accent
                                       : variant === "danger" ? Tokens.Theme.dangerSurface
                                       : variant === "secondary" ? Tokens.Theme.surfaceElevated
                                       : "transparent"
    readonly property color labelColor: variant === "primary" ? Tokens.Theme.accentText
                                        : variant === "danger" ? Tokens.Theme.danger
                                        : Tokens.Theme.textPrimary

    implicitHeight: Tokens.Theme.controlHeight
    implicitWidth: Math.max(94, contentItem.implicitWidth + 2 * Tokens.Theme.spaceMd)
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: text

    contentItem: RowLayout {
        spacing: Tokens.Theme.spaceSm
        Image {
            visible: control.iconSource.toString().length > 0
            source: control.iconSource
            sourceSize.width: 18
            sourceSize.height: 18
            Layout.preferredWidth: visible ? 18 : 0
            Layout.preferredHeight: 18
        }
        Label {
            text: control.text
            color: control.enabled ? control.labelColor : Tokens.Theme.textMuted
            font.pixelSize: Tokens.Theme.textBody
            font.weight: Tokens.Theme.weightDemiBold
            Layout.alignment: Qt.AlignHCenter
            horizontalAlignment: Text.AlignHCenter
        }
    }

    background: Rectangle {
        radius: Tokens.Theme.radiusSm
        color: !control.enabled ? Tokens.Theme.surfaceElevated
             : control.down ? Tokens.Theme.hoverSurface
             : control.hovered && control.variant !== "primary" ? Tokens.Theme.hoverSurface
             : control.fillColor
        border.width: control.activeFocus ? 2 : control.variant === "secondary" ? 1 : 0
        border.color: control.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
    }
}
