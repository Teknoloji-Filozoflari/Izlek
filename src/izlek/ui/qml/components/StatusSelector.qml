import QtQuick

SegmentedControl {
    id: selector
    property string status: ""
    readonly property var statuses: ["PLANNED", "WATCHING", "WATCHED"]
    signal statusSelected(string status)
    options: [
        (i18n.revision, i18n.t("status.planned")),
        (i18n.revision, i18n.t("status.watching")),
        (i18n.revision, i18n.t("status.watched"))
    ]
    onStatusChanged: currentIndex = statuses.indexOf(status)
    Component.onCompleted: currentIndex = statuses.indexOf(status)
    onSelected: function(index) {
        status = statuses[index]
        statusSelected(status)
    }
}
