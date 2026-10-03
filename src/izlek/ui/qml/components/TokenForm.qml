import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

ColumnLayout {
    id: form
    property var controller
    property string heading: "TMDb bağlantısı"
    property string description: "TMDb API ayarlarındaki Read Access Token değerini girin."
    function clearInput() { tokenField.clear() }
    spacing: Tokens.Theme.spaceMd

    Label {
        text: form.heading
        color: Tokens.Theme.textPrimary
        font.pixelSize: Tokens.Theme.textHeading
        font.weight: Tokens.Theme.weightDemiBold
        Layout.fillWidth: true
    }
    Label {
        text: form.description
        color: Tokens.Theme.textSecondary
        font.pixelSize: Tokens.Theme.textBody
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    Label {
        text: "TMDb Read Access Token"
        color: Tokens.Theme.textPrimary
        font.pixelSize: Tokens.Theme.textBody
        Layout.topMargin: Tokens.Theme.spaceSm
    }
    TextField {
        id: tokenField
        objectName: "tokenInput"
        readonly property bool passwordMasked: echoMode === TextInput.Password
        Layout.fillWidth: true
        implicitHeight: Tokens.Theme.controlHeight + 6
        placeholderText: "Tokenı buraya yapıştırın"
        echoMode: TextInput.Password
        inputMethodHints: Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
        color: Tokens.Theme.textPrimary
        placeholderTextColor: Tokens.Theme.textMuted
        selectionColor: Tokens.Theme.accentSurface
        selectedTextColor: Tokens.Theme.textPrimary
        font.pixelSize: Tokens.Theme.textBody
        enabled: !form.controller.busy
        Accessible.name: "TMDb Read Access Token"
        onAccepted: if (text.trim().length > 0) form.controller.testToken(text)
        background: Rectangle {
            color: Tokens.Theme.surfaceElevated
            radius: Tokens.Theme.radiusSm
            border.width: tokenField.activeFocus ? 2 : 1
            border.color: tokenField.activeFocus ? Tokens.Theme.accent : Tokens.Theme.border
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Tokens.Theme.spaceSm
        IzlekButton {
            objectName: "testTokenButton"
            text: "Tokenı Test Et"
            variant: "secondary"
            enabled: !form.controller.busy && tokenField.text.trim().length > 0
            onClicked: form.controller.testToken(tokenField.text)
        }
        IzlekButton {
            objectName: "saveTokenButton"
            text: form.controller.busy ? "Doğrulanıyor…" : "Kaydet"
            enabled: !form.controller.busy && tokenField.text.trim().length > 0
            onClicked: form.controller.saveToken(tokenField.text)
        }
        Item { Layout.fillWidth: true }
    }

    Label {
        objectName: "tokenFeedback"
        text: form.controller.feedback
        visible: text.length > 0
        color: form.controller.feedbackKind === "danger" ? Tokens.Theme.danger
               : form.controller.feedbackKind === "warning" ? Tokens.Theme.warning
               : Tokens.Theme.success
        font.pixelSize: Tokens.Theme.textBody
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
        Accessible.name: text
    }
    Label {
        text: "Sistem anahtarlığı kullanılamazsa token, yalnızca hesabınızın "
              + "okuyabildiği yerel bir dosyada düz metin olarak saklanır."
        color: Tokens.Theme.textMuted
        font.pixelSize: Tokens.Theme.textSmall
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    Connections {
        target: form.controller
        function onTokenSaved() { form.clearInput() }
    }
}
