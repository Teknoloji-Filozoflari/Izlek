import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as Tokens

ColumnLayout {
    id: panel
    property var stats: ({})
    readonly property var genres: stats.genre_distribution || []
    readonly property var shows: stats.top_shows || []
    readonly property var months: stats.monthly_activity || []
    readonly property var history: stats.recent_history || []
    readonly property int maxMonthMinutes: {
        var peak = 0
        for (var i = 0; i < months.length; i++)
            peak = Math.max(peak, months[i].minutes || 0)
        return peak
    }
    readonly property var chartColors: [Tokens.Theme.accent, Tokens.Theme.chartBlue,
        Tokens.Theme.success, Tokens.Theme.warning, Tokens.Theme.danger]
    spacing: Tokens.Theme.spaceMd

    function durationText(minutes) {
        if (minutes === undefined || minutes === null) return "Süre bilgisi eksik"
        var days = Math.floor(minutes / 1440)
        var hours = Math.floor((minutes % 1440) / 60)
        return (days > 0 ? days + " gün " : "") + (hours > 0 ? hours + " sa " : "") + minutes % 60 + " dk"
    }

    function historyDate(value) {
        if (!value) return ""
        return String(value).slice(0, 10)
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
        columns: panel.width >= 900 ? 4 : 2
        columnSpacing: Tokens.Theme.spaceSm
        rowSpacing: Tokens.Theme.spaceSm
        Repeater {
            model: [
                {label: (i18n.revision, i18n.t("stats.watched_episodes")), value: panel.stats.watched_episodes || 0},
                {label: (i18n.revision, i18n.t("stats.watched_movies")), value: panel.stats.watched_movies || 0},
                {label: "Tamamlanan dizi", value: panel.stats.completed_tv || 0},
                {label: "Film yeniden izleme", value: panel.stats.movie_rewatch_count || 0}
