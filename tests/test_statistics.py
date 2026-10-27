"""Local-only aggregate statistics and missing-runtime behavior."""

from concurrent.futures import Future
from datetime import date, datetime
from pathlib import Path

import pytest

from izlek.app import create_application
from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import (
    EpisodeRepository,
    MediaRepository,
    SeasonRepository,
    UserMediaRepository,
)
from izlek.security.token_store import StoredToken
from izlek.services.continue_watching import ContinueWatchingService
from izlek.services.movie_library import MovieLibraryService
from izlek.services.statistics import StatisticsService
from izlek.services.tv_library import TvLibraryService
from izlek.ui.controllers.continue_watching_controller import ContinueWatchingController
from izlek.ui.controllers.movie_library_controller import MovieLibraryController
from izlek.ui.controllers.statistics_controller import StatisticsController
from izlek.ui.controllers.token_controller import TokenController
from izlek.ui.controllers.tv_library_controller import TvLibraryController


class _Store:
    def load(self):
        return StoredToken("test-only", "keyring")


class _Images:
    def poster(self, path):
        future = Future()
        future.set_result(
            Path(__file__).resolve().parents[1]
            / "src/izlek/resources/images/poster-placeholder.svg"
        )
        return future

    def backdrop(self, path):
        return self.poster(path)


def test_empty_statistics_snapshot_has_stable_zero_values(tmp_path):
    engine = initialize_database(tmp_path / "empty.sqlite3")
    try:
        snapshot = StatisticsService(create_session_factory(engine)).snapshot()
        values = snapshot.as_dict()
        monthly = values.pop("monthly_activity")
        assert len(monthly) == 12
        assert monthly[0]["movies"] == 0
        assert monthly[0]["episodes"] == 0
        assert values.pop("top_shows") == []
        assert values.pop("genre_distribution") == []
        assert values.pop("recent_history") == []
        assert values == {
            "watched_movies": 0,
            "completed_tv": 0,
            "watched_episodes": 0,
            "watched_movie_minutes": 0,
            "watched_episode_minutes": 0,
            "estimated_total_minutes": 0,
            "missing_movie_runtime_count": 0,
            "missing_episode_runtime_count": 0,
            "favorite_movies": 0,
            "favorite_tv": 0,
            "planned_movies": 0,
            "planned_tv": 0,
            "movie_rewatch_count": 0,
            "top_genres": [],
        }
    finally:
        engine.dispose()


@pytest.mark.parametrize("unknown_runtime", [None, 0, -1])
@pytest.mark.parametrize("include_known", [False, True])
def test_invalid_runtimes_are_excluded_without_hiding_totals(
    tmp_path, unknown_runtime, include_known
):
    engine = initialize_database(tmp_path / "runtimes.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session)
        users = UserMediaRepository(session)
        movie = media.upsert(1, MediaType.MOVIE, "Unknown", runtime=unknown_runtime)
        users.set_status(movie.id, TrackingStatus.WATCHED)
        show = media.upsert(1, MediaType.TV, "Show")
        season = SeasonRepository(session).upsert(show.id, 1)
        episodes = EpisodeRepository(session)
        episode = episodes.upsert(season.id, 1, runtime=unknown_runtime)
        episodes.set_watched(episode.id, True)
        if include_known:
            movie = media.upsert(2, MediaType.MOVIE, "Known", runtime=100)
            users.set_status(movie.id, TrackingStatus.WATCHED)
            episode = episodes.upsert(season.id, 2, runtime=40)
            episodes.set_watched(episode.id, True)
    try:
        result = StatisticsService(factory).snapshot()
        assert result.watched_movie_minutes == (100 if include_known else 0)
        assert result.watched_episode_minutes == (40 if include_known else 0)
        assert result.estimated_total_minutes == (140 if include_known else 0)
        assert result.missing_movie_runtime_count == 1
        assert result.missing_episode_runtime_count == 1
        assert result.watched_movies == (2 if include_known else 1)
        assert result.watched_episodes == (2 if include_known else 1)
        assert result.top_shows[0]["minutes"] == (40 if include_known else 0)
    finally:
        engine.dispose()


def test_statistics_uses_local_tracking_and_sums_known_durations(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session)
        users = UserMediaRepository(session)
        seasons = SeasonRepository(session)
        episodes = EpisodeRepository(session)

        watched_movie = media.upsert(
            1,
            MediaType.MOVIE,
            "Known runtime",
            runtime=100,
            metadata_json={"detail": {"genres": [{"name": "Dram"}]}},
        )
        users.set_status(watched_movie.id, TrackingStatus.WATCHED)
        unknown_movie = media.upsert(
            2,
            MediaType.MOVIE,
            "Unknown runtime",
            metadata_json={"detail": {"genres": [{"name": "Aksiyon"}]}},
        )
        users.set_status(unknown_movie.id, TrackingStatus.WATCHED)
        planned_movie = media.upsert(3, MediaType.MOVIE, "Planned")
        users.set_status(planned_movie.id, TrackingStatus.PLANNED)
        users.set_favorite(planned_movie.id, True)

        completed = media.upsert(
            4,
            MediaType.TV,
            "Completed show",
            metadata_json={"detail": {"genres": [{"name": "Dram"}]}},
        )
        users.set_status(completed.id, TrackingStatus.WATCHED)
        users.set_favorite(completed.id, True)
        planned_show = media.upsert(5, MediaType.TV, "Planned show")
        users.set_status(planned_show.id, TrackingStatus.PLANNED)
        users.set_favorite(planned_show.id, True)
        season = seasons.upsert(completed.id, 1)
        known_episode = episodes.upsert(season.id, 1, runtime=50)
        unknown_episode = episodes.upsert(season.id, 2)
        episodes.set_watched(known_episode.id, True)
        episodes.set_watched(unknown_episode.id, True)

    service = StatisticsService(factory)
    incomplete = service.snapshot()
    assert incomplete.watched_movies == 2
    assert incomplete.completed_tv == 1
    assert incomplete.watched_episodes == 2
    assert incomplete.watched_movie_minutes == 100
    assert incomplete.watched_episode_minutes == 50
    assert incomplete.estimated_total_minutes == 150
    assert incomplete.missing_movie_runtime_count == 1
    assert incomplete.missing_episode_runtime_count == 1
    assert incomplete.favorite_movies == 1
    assert incomplete.favorite_tv == 2
    assert incomplete.planned_movies == 1
    assert incomplete.planned_tv == 1
    assert incomplete.top_genres == [
        {"name": "Dram", "count": 2},
        {"name": "Aksiyon", "count": 1},
    ]

    with factory.begin() as session:
        media = MediaRepository(session)
        media.upsert(
            2,
            MediaType.MOVIE,
            "Unknown runtime",
            runtime=90,
            metadata_json={"detail": {"genres": [{"name": "Aksiyon"}]}},
        )
        episode = EpisodeRepository(session).get(unknown_episode.id)
        assert episode is not None
        EpisodeRepository(session).upsert(episode.season_id, 2, runtime=40)

    complete = service.snapshot()
    assert complete.watched_movie_minutes == 190
    assert complete.watched_episode_minutes == 90
    assert complete.estimated_total_minutes == 280
    assert complete.missing_movie_runtime_count == 0
    assert complete.missing_episode_runtime_count == 0
    engine.dispose()


def test_dashboard_shows_local_statistics_and_opens_detail(tmp_path, monkeypatch):
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuick import QQuickItem
    from PySide6.QtTest import QTest

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    application = QGuiApplication.instance() or QGuiApplication([])
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(
            10, MediaType.MOVIE, "Watched", runtime=95
        )
        UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHED)
        unknown = MediaRepository(session).upsert(11, MediaType.MOVIE, "Unknown")
        UserMediaRepository(session).set_status(unknown.id, TrackingStatus.WATCHED)
    statistics = StatisticsController(service=StatisticsService(factory))
    movie_library = MovieLibraryController(
        service=MovieLibraryService(factory), images=_Images()
    )
    tv_library = TvLibraryController(
        service=TvLibraryService(factory), images=_Images()
    )
    continuing = ContinueWatchingController(
        service=ContinueWatchingService(factory), images=_Images()
    )
    application, qml_engine, window = create_application(
        token_controller=TokenController(store=_Store()),
        statistics_controller=statistics,
        movie_library_controller=movie_library,
        tv_library_controller=tv_library,
        continue_controller=continuing,
    )
    try:
        window.navigate(4)
        dashboard = window.findChild(QQuickItem, "dashboardStats")
        for _ in range(100):
            application.processEvents()
            if (
                not statistics.busy
                and statistics.stats.get("watched_movies") == 2
                and dashboard.isVisible()
            ):
                break
            QTest.qWait(10)
        else:
            raise AssertionError("İstatistikler yüklenmedi")
        assert dashboard is not None and dashboard.isVisible()
        for width, height in ((800, 600), (1366, 768), (1920, 1080)):
            window.resize(width, height)
            application.processEvents()
            QTest.qWait(50)
            assert dashboard.width() > 260 and dashboard.height() > 200
            assert abs(dashboard.width() - dashboard.parentItem().width()) < 1
            assert dashboard.width() > width - 350
            summary = window.findChild(QQuickItem, "durationSummary")
            charts = window.findChild(QQuickItem, "statisticsCharts")
            assert summary.property("columns") == (3 if width >= 1366 else 1)
            assert charts.property("columns") == (2 if width >= 1366 else 1)
        total = window.findChild(QQuickItem, "totalScreenTime")
        movie_time = window.findChild(QQuickItem, "movieScreenTime")
        episode_time = window.findChild(QQuickItem, "episodeScreenTime")
        assert total.property("value") == movie_time.property("value") == "1 sa 35 dk"
        assert episode_time.property("value") == "0 dk"
        assert window.findChild(QQuickItem, "totalScreenTime") is not None
        assert statistics.stats["estimated_total_minutes"] == 95
        description = window.findChild(QQuickItem, "screenTimeDescription")
        assert "1 film ve 0 bölüm hesaba katılmadı" in description.property("text")
        assert window.findChild(QQuickItem, "monthlyStatistics") is not None
        assert window.findChild(QQuickItem, "recentHistoryStatistics") is not None
        assert window.findChild(QQuickItem, "genreStatistics") is not None
        assert window.findChild(QQuickItem, "topShowStatistics") is not None
    finally:
        window.close()
        statistics.close()
        movie_library.close()
        tv_library.close()
        continuing.close()
        application.processEvents()
        engine.dispose()


def test_monthly_activity_uses_watch_dates_and_top_shows_use_real_runtimes(tmp_path):
    engine = initialize_database(tmp_path / "activity.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(
            77,
            MediaType.TV,
            "Friends",
            poster_path="/friends.jpg",
            metadata_json={
                "detail": {"genres": [{"name": "Komedi"}, {"name": "Dram"}]}
            },
        )
        season = SeasonRepository(session).upsert(media.id, 1)
        for number, runtime, watched_at in (
            (1, 25, datetime(2025, 2, 1)),
            (2, 30, datetime(2025, 12, 31)),
            (3, 40, datetime(2026, 1, 10)),
            (4, None, datetime(2026, 1, 11)),
            (5, 20, None),
            (6, 50, datetime(2025, 1, 1)),
        ):
            episode = EpisodeRepository(session).upsert(
                season.id, number, runtime=runtime
            )
            progress = EpisodeRepository(session).set_watched(episode.id, True)
            progress.watched_at = watched_at
        movie = MediaRepository(session).upsert(
            88,
            MediaType.MOVIE,
            "January Film",
            runtime=110,
            release_date=date(2024, 5, 1),
            metadata_json={"detail": {"genres": [{"name": "Dram"}]}},
        )
        user = UserMediaRepository(session).set_status(movie.id, TrackingStatus.WATCHED)
        user.watched_at = datetime(2026, 1, 12)
        user.rewatch_count = 2
    try:
        result = StatisticsService(factory).snapshot(today=date(2026, 1, 31))
        assert len(result.monthly_activity) == 12
        assert result.monthly_activity[0]["month"] == 2
        assert result.monthly_activity[0]["year"] == 2025
        assert result.monthly_activity[0]["minutes"] == 25
        assert result.monthly_activity[0]["movies"] == 0
        assert result.monthly_activity[-2]["minutes"] == 30
        assert result.monthly_activity[-1]["minutes"] == 150
        assert result.monthly_activity[-1]["episodes"] == 2
        assert result.monthly_activity[-1]["movies"] == 1
        assert result.monthly_activity[-1]["movie_minutes"] == 110
        assert result.monthly_activity[-1]["missing_runtime"] == 1
        assert result.top_shows[0]["title"] == "Friends"
        assert result.top_shows[0]["minutes"] == 165
        assert result.top_shows[0]["missing_runtime"] == 1
        assert result.watched_episode_minutes == 165
        assert result.watched_movie_minutes == 110
        assert result.estimated_total_minutes == 275
        assert result.movie_rewatch_count == 2
        assert result.recent_history[0]["title"] == "January Film"
        assert result.recent_history[0]["kind"] == "movie"
        assert result.recent_history[0]["rewatchCount"] == 2
        assert any(item["kind"] == "episode" for item in result.recent_history)
        assert sum(row["share"] for row in result.genre_distribution) == 1
        # Unmarking immediately removes the episode from charts and totals.
        with factory.begin() as session:
            EpisodeRepository(session).set_watched(episode.id, False)
        assert StatisticsService(factory).snapshot().top_shows[0]["episodes"] == 5
    finally:
        engine.dispose()


def test_movie_watched_at_and_rewatch_count_round_trip(tmp_path):
    engine = initialize_database(tmp_path / "rewatch.sqlite3")
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            movie = MediaRepository(session).upsert(
                9, MediaType.MOVIE, "Rewatchable", runtime=95
            )
            users = UserMediaRepository(session)
            first = users.set_status(movie.id, TrackingStatus.WATCHED)
            assert first.watched_at is not None
            assert first.rewatch_count == 0
            stamped = first.watched_at
            noop = users.set_status(movie.id, TrackingStatus.WATCHED)
            assert noop.rewatch_count == 0
            assert noop.watched_at == stamped
            second = users.set_status(movie.id, TrackingStatus.WATCHED, rewatch=True)
            assert second.rewatch_count == 1
            assert second.watched_at >= stamped
            users.set_status(movie.id, TrackingStatus.PLANNED)
            cleared = users.get(movie.id)
            assert cleared.watched_at is None
            assert cleared.rewatch_count == 1
            restored = users.set_status(movie.id, TrackingStatus.WATCHED)
            assert restored.watched_at is not None
            assert restored.rewatch_count == 1
    finally:
        engine.dispose()
