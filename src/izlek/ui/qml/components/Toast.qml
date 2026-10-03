import QtQuick
import QtQuick.Controls
import "../theme" as Tokens

Popup {
    id: toast
    property string message: ""
    property string tone: "neutral"
    modal: false
    focus: false
    padding: Tokens.Theme.spaceMd
    implicitWidth: Math.min(420, parent ? parent.width - 2 * Tokens.Theme.spaceLg : 420)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? parent.height - height - Tokens.Theme.spaceLg : 0
    closePolicy: Popup.NoAutoClose

    function show(text, appearance) {
        message = text
        tone = appearance || "neutral"
        open()
        hideTimer.restart()
    }

    contentItem: Label {
        text: toast.message
        color: Tokens.Theme.textPrimary
        font.pixelSize: Tokens.Theme.textBody
        wrapMode: Text.WordWrap
    }
    background: Rectangle {
        color: Tokens.Theme.surfaceElevated
        radius: Tokens.Theme.radiusSm
        border.width: 1
        border.color: toast.tone === "danger" ? Tokens.Theme.danger
                    : toast.tone === "success" ? Tokens.Theme.success
                    : Tokens.Theme.accent
    }
    Timer {
        id: hideTimer
        interval: 3000
        onTriggered: toast.close()
    }
}
