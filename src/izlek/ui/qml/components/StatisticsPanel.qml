import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

ColumnLayout {
    id: panel
    property var stats: ({})
    readonly property var genres: stats.genre_distribution || []
    readonly property var shows: stats.top_shows || []
    readonly property var chartColors: [Tokens.Theme.statsAccent, Tokens.Theme.accent, Tokens.Theme.chartBlue, Tokens.Theme.danger, Tokens.Theme.textMuted]
    spacing: Tokens.Theme.spaceMd
    function durationText(minutes) {
        if (minutes === undefined || minutes === null) return "Süre bilgisi eksik"
        var days = Math.floor(minutes / 1440)
        var hours = Math.floor((minutes % 1440) / 60)
        return (days > 0 ? days + " gün " : "") + (hours > 0 ? hours + " sa " : "") + minutes % 60 + " dk"
    }
    Rectangle {
        objectName: "totalScreenTime"
        Layout.fillWidth: true
        Layout.preferredHeight: 150
        color: Tokens.Theme.statsAccent
        radius: Tokens.Theme.radiusLg
        clip: true
        Label {
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: Tokens.Theme.spaceLg
            text: "✓"; opacity: 0.12; color: Tokens.Theme.statsAccentText; font.pixelSize: 130
        }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: Tokens.Theme.spaceLg; spacing: Tokens.Theme.spaceXs
            Label { text: "TOPLAM EKRAN SÜRESİ"; color: Tokens.Theme.statsAccentText; font.pixelSize: Tokens.Theme.textSmall; font.weight: Tokens.Theme.weightDemiBold; font.letterSpacing: 1 }
            Label { Layout.fillWidth: true; text: panel.durationText(panel.stats.estimated_total_minutes); color: Tokens.Theme.statsAccentText; font.pixelSize: Tokens.Theme.textStat + 8; font.weight: Tokens.Theme.weightDemiBold; elide: Text.ElideRight }
            Label {
                objectName: "screenTimeDescription"
                Layout.fillWidth: true
                text: {
                    var movies = panel.stats.missing_movie_runtime_count || 0
                    var episodes = panel.stats.missing_episode_runtime_count || 0
                    if (movies || episodes)
                        return "Süresi bilinen içeriklerden hesaplandı. Süresi bilinmeyen "
                               + movies + " film ve " + episodes + " bölüm hesaba katılmadı."
                    return "İzlediğin film ve bölümlerden hesaplandı."
                }
                color: Tokens.Theme.statsAccentText
                wrapMode: Text.WordWrap
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true; spacing: Tokens.Theme.spaceSm
        Repeater {
            model: [{label: "İzlenen bölüm", value: panel.stats.watched_episodes || 0}, {label: "İzlenen film", value: panel.stats.watched_movies || 0}, {label: "Tamamlanan dizi", value: panel.stats.completed_tv || 0}]
            Rectangle {
                required property var modelData
                Layout.fillWidth: true; Layout.preferredHeight: 84
                color: Tokens.Theme.surface; radius: Tokens.Theme.radiusMd; border.color: Tokens.Theme.border
                Column {
                    anchors.centerIn: parent; spacing: Tokens.Theme.spaceXs
                    Label { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.value; color: Tokens.Theme.textPrimary; font.pixelSize: Tokens.Theme.textHeading; font.weight: Tokens.Theme.weightDemiBold }
                    Label { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: Tokens.Theme.textMuted; font.pixelSize: Tokens.Theme.textSmall }
                }
            }
        }
    }
    Rectangle {
        objectName: "genreStatistics"
        Layout.fillWidth: true; Layout.preferredHeight: 172
        color: Tokens.Theme.surface; radius: Tokens.Theme.radiusLg; border.color: Tokens.Theme.border
        RowLayout {
            anchors.fill: parent; anchors.margins: Tokens.Theme.spaceMd; spacing: Tokens.Theme.spaceLg
            Item {
                Layout.preferredWidth: 124; Layout.preferredHeight: 124
                Canvas {
                    anchors.fill: parent
                    property var chartData: panel.genres
                    onChartDataChanged: requestPaint()
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)
                        var angle = -Math.PI / 2
                        ctx.lineWidth = 26
                        if (chartData.length === 0) {
                            ctx.beginPath(); ctx.strokeStyle = Tokens.Theme.border
                            ctx.arc(width / 2, height / 2, 48, 0, Math.PI * 2); ctx.stroke()
                        }
                        for (var i = 0; i < chartData.length; i++) {
                            var end = angle + chartData[i].share * Math.PI * 2
                            ctx.beginPath(); ctx.strokeStyle = panel.chartColors[i % panel.chartColors.length]
                            ctx.arc(width / 2, height / 2, 48, angle, end); ctx.stroke(); angle = end
                        }
                    }
                }
                Label { anchors.centerIn: parent; text: "Türler"; color: Tokens.Theme.textPrimary; font.weight: Tokens.Theme.weightDemiBold }
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: Tokens.Theme.spaceXs
                Label { visible: panel.genres.length === 0; text: "Henüz tür verisi yok."; color: Tokens.Theme.textMuted }
                Repeater {
                    model: panel.genres
                    RowLayout {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        Rectangle { implicitWidth: 10; implicitHeight: 10; radius: 3; color: panel.chartColors[index % panel.chartColors.length] }
                        Label { Layout.fillWidth: true; text: modelData.name; color: Tokens.Theme.textPrimary; elide: Text.ElideRight }
                        Label { text: Math.round(modelData.share * 100) + "%"; color: Tokens.Theme.textMuted; font.pixelSize: Tokens.Theme.textSmall }
                    }
                }
            }
        }
    }
    Rectangle {
        objectName: "topShowStatistics"
        Layout.fillWidth: true; Layout.preferredHeight: topShowsColumn.implicitHeight + 2 * Tokens.Theme.spaceMd
        color: Tokens.Theme.surface; radius: Tokens.Theme.radiusLg; border.color: Tokens.Theme.border
        ColumnLayout {
            id: topShowsColumn
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: Tokens.Theme.spaceMd
            spacing: Tokens.Theme.spaceMd
            Label { text: "En çok zaman ayırdığın diziler"; color: Tokens.Theme.textPrimary; font.weight: Tokens.Theme.weightDemiBold }
            Label { visible: panel.shows.length === 0; text: "Bölüm izledikçe dizilerin burada görünür."; color: Tokens.Theme.textMuted }
            Repeater {
                model: panel.shows
                RowLayout {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true; spacing: Tokens.Theme.spaceSm
                    Label { text: index + 1; color: Tokens.Theme.textMuted }
                    Image { Layout.preferredWidth: 34; Layout.preferredHeight: 51; source: modelData.poster || ""; asynchronous: true; fillMode: Image.PreserveAspectCrop; sourceSize.width: 68 }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: Tokens.Theme.spaceXs
                        RowLayout {
                            Layout.fillWidth: true
                            Label { Layout.fillWidth: true; text: modelData.title; color: Tokens.Theme.textPrimary; elide: Text.ElideRight }
                            Label { text: panel.durationText(modelData.minutes); color: Tokens.Theme.textMuted; font.pixelSize: Tokens.Theme.textSmall }
                        }
                        Rectangle {
                            Layout.fillWidth: true; implicitHeight: 5; radius: 3; color: Tokens.Theme.border
                            Rectangle { width: parent.width * modelData.minutes / Math.max(1, panel.shows[0].minutes); height: parent.height; radius: parent.radius; color: Tokens.Theme.statsAccent }
                        }
                    }
                }
            }
        }
    }
}
