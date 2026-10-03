import QtQuick

SegmentedControl {
    id: selector
    property string status: ""
    readonly property var statuses: ["PLANNED", "WATCHING", "WATCHED"]
    signal statusSelected(string status)
    options: ["İzlenecek", "İzleniyor", "İzlendi"]
    onStatusChanged: currentIndex = statuses.indexOf(status)
    Component.onCompleted: currentIndex = statuses.indexOf(status)
    onSelected: function(index) {
        status = statuses[index]
        statusSelected(status)
    }
}
