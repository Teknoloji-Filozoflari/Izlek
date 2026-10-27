import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

ColumnLayout {
    id: panel
    property var stats: ({})
    readonly property var genres: stats.genre_distribution || []
    readonly property var shows: stats.top_shows || []
    readonly property var chartColors: [Tokens.Theme.accent, Tokens.Theme.chartBlue,
        Tokens.Theme.success, Tokens.Theme.warning, Tokens.Theme.danger]
    spacing: Tokens.Theme.spaceMd

    function durationText(minutes) {
        if (minutes === undefined || minutes === null) return "Süre bilgisi eksik"
        var days = Math.floor(minutes / 1440)
        var hours = Math.floor((minutes % 1440) / 60)
        return (days > 0 ? days + " gün " : "") + (hours > 0 ? hours + " sa " : "") + minutes % 60 + " dk"
    }

    GridLayout {
        objectName: "durationSummary"
        Layout.fillWidth: true
        columns: panel.width >= 900 ? 3 : 1
        columnSpacing: Tokens.Theme.spaceSm
        rowSpacing: Tokens.Theme.spaceSm
        StatCard {
            objectName: "totalScreenTime"
            Layout.fillWidth: true
            label: "Toplam ekran süresi"
            value: panel.durationText(panel.stats.estimated_total_minutes)
            detail: "Film ve bölümler"
            accented: true
        }
        StatCard {
            objectName: "movieScreenTime"
            Layout.fillWidth: true
            label: "Film süresi"
            value: panel.durationText(panel.stats.watched_movie_minutes)
            detail: (panel.stats.watched_movies || 0) + " izlenen film"
        }
        StatCard {
            objectName: "episodeScreenTime"
            Layout.fillWidth: true
            label: "Bölüm süresi"
            value: panel.durationText(panel.stats.watched_episode_minutes)
            detail: (panel.stats.watched_episodes || 0) + " izlenen bölüm"
        }
    }
    Label {
        objectName: "screenTimeDescription"
        Layout.fillWidth: true
        text: {
            var movies = panel.stats.missing_movie_runtime_count || 0
            var episodes = panel.stats.missing_episode_runtime_count || 0
            if (movies || episodes)
                return "Süresi bilinen içeriklerden hesaplandı. Süresi bilinmeyen "
                       + movies + " film ve " + episodes + " bölüm hesaba katılmadı."
            return "Süreler, izlediğin film ve bölümlerin bilinen sürelerinden hesaplandı."
        }
        color: Tokens.Theme.textMuted
        font.pixelSize: Tokens.Theme.textSmall
        wrapMode: Text.WordWrap
    }
    GridLayout {
        Layout.fillWidth: true
        columns: 3
        columnSpacing: Tokens.Theme.spaceSm
        Repeater {
            model: [
                {label: (i18n.revision, i18n.t("stats.watched_episodes")), value: panel.stats.watched_episodes || 0},
                {label: (i18n.revision, i18n.t("stats.watched_movies")), value: panel.stats.watched_movies || 0},
                {label: "Tamamlanan dizi", value: panel.stats.completed_tv || 0}
            ]
            StatCard {
                required property var modelData
                Layout.fillWidth: true
                implicitWidth: 0
                implicitHeight: 96
                label: modelData.label
                value: String(modelData.value)
            }
        }
    }
    GridLayout {
        objectName: "statisticsCharts"
        Layout.fillWidth: true
        columns: panel.width >= 900 ? 2 : 1
        columnSpacing: Tokens.Theme.spaceMd
        rowSpacing: Tokens.Theme.spaceMd
        Rectangle {
            objectName: "genreStatistics"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 1
            implicitHeight: genreColumn.implicitHeight + 2 * Tokens.Theme.spaceMd
            color: Tokens.Theme.surface
            radius: Tokens.Theme.radiusLg
            border.color: Tokens.Theme.border
            ColumnLayout {
                id: genreColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Tokens.Theme.spaceMd
                spacing: Tokens.Theme.spaceMd
                Label {
                    text: (i18n.revision, i18n.t("stats.genres_title"))
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textEmpty
                    font.weight: Tokens.Theme.weightDemiBold
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Tokens.Theme.spaceMd
                    Item {
                        Layout.preferredWidth: 124
                        Layout.preferredHeight: 124
                        Canvas {
                            anchors.fill: parent
                            property var chartData: panel.genres
                            onChartDataChanged: requestPaint()
                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.clearRect(0, 0, width, height)
                                var angle = -Math.PI / 2
                                ctx.lineWidth = 22
                                if (chartData.length === 0) {
                                    ctx.beginPath()
                                    ctx.strokeStyle = Tokens.Theme.border
                                    ctx.arc(width / 2, height / 2, 48, 0, Math.PI * 2)
                                    ctx.stroke()
                                }
                                for (var i = 0; i < chartData.length; i++) {
                                    var end = angle + chartData[i].share * Math.PI * 2
                                    ctx.beginPath()
                                    ctx.strokeStyle = panel.chartColors[i % panel.chartColors.length]
                                    ctx.arc(width / 2, height / 2, 48, angle, end)
                                    ctx.stroke()
                                    angle = end
                                }
                            }
                        }
                        Label {
                            anchors.centerIn: parent
                            text: (i18n.revision, i18n.t("stats.genres"))
                            color: Tokens.Theme.textSecondary
                            font.pixelSize: Tokens.Theme.textSmall
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Tokens.Theme.spaceSm
                        Label {
                            visible: panel.genres.length === 0
                            Layout.fillWidth: true
                            text: (i18n.revision, i18n.t("stats.genres_empty"))
                            color: Tokens.Theme.textMuted
                            wrapMode: Text.WordWrap
                        }
                        Repeater {
                            model: panel.genres
                            RowLayout {
                                required property var modelData
                                required property int index
                                Layout.fillWidth: true
                                spacing: Tokens.Theme.spaceXs
                                Rectangle {
                                    implicitWidth: 8
                                    implicitHeight: 8
                                    radius: 4
                                    color: panel.chartColors[index % panel.chartColors.length]
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    color: Tokens.Theme.textPrimary
                                    elide: Text.ElideRight
                                }
                                Label {
                                    objectName: "genreCount"
                                    text: modelData.count + " içerik · " + Math.round(modelData.share * 100) + "%"
                                    color: Tokens.Theme.textSecondary
                                    font.pixelSize: Tokens.Theme.textSmall
                                }
                            }
                        }
                    }
                }
                Label {
                    Layout.fillWidth: true
                    text: (i18n.revision, i18n.t("stats.genres_note"))
                    color: Tokens.Theme.textMuted
                    font.pixelSize: Tokens.Theme.textSmall
                    wrapMode: Text.WordWrap
                }
            }
        }
        Rectangle {
            objectName: "topShowStatistics"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 1
            implicitHeight: topShowsColumn.implicitHeight + 2 * Tokens.Theme.spaceMd
            color: Tokens.Theme.surface
            radius: Tokens.Theme.radiusLg
            border.color: Tokens.Theme.border
            ColumnLayout {
                id: topShowsColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Tokens.Theme.spaceMd
                spacing: Tokens.Theme.spaceMd
                Label {
                    Layout.fillWidth: true
                    text: (i18n.revision, i18n.t("stats.top_shows"))
                    color: Tokens.Theme.textPrimary
                    font.pixelSize: Tokens.Theme.textEmpty
                    font.weight: Tokens.Theme.weightDemiBold
                    wrapMode: Text.WordWrap
                }
                Label {
                    visible: panel.shows.length === 0
                    Layout.fillWidth: true
                    text: (i18n.revision, i18n.t("stats.top_shows_empty"))
                    color: Tokens.Theme.textMuted
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: panel.shows
                    RowLayout {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        spacing: Tokens.Theme.spaceSm
                        Label {
                            text: index + 1
                            color: Tokens.Theme.textMuted
                        }
                        Image {
                            Layout.preferredWidth: 34
                            Layout.preferredHeight: 51
                            source: modelData.poster || ""
                            asynchronous: true
                            fillMode: Image.PreserveAspectCrop
                            sourceSize.width: 68
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Tokens.Theme.spaceXs
                            Label {
                                Layout.fillWidth: true
                                text: modelData.title
                                color: Tokens.Theme.textPrimary
                                elide: Text.ElideRight
                            }
                            Label {
                                objectName: "showDuration"
                                Layout.fillWidth: true
                                text: modelData.episodes + " bölüm · " + panel.durationText(modelData.minutes)
                                    + (modelData.missing_runtime ? " · " + modelData.missing_runtime + " bölümün süresi eksik" : "")
                                color: Tokens.Theme.textSecondary
                                font.pixelSize: Tokens.Theme.textSmall
                                wrapMode: Text.WordWrap
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 4
                                radius: 2
                                color: Tokens.Theme.border
                                Rectangle {
                                    width: parent.width * modelData.minutes / Math.max(1, panel.shows[0].minutes)
                                    height: parent.height
                                    radius: parent.radius
                                    color: Tokens.Theme.accent
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
