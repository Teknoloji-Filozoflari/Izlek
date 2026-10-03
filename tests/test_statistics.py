"""Local-only aggregate statistics and missing-runtime behavior."""

from concurrent.futures import Future
from pathlib import Path

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
        assert snapshot.as_dict() == {
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
            "top_genres": [],
        }
    finally:
        engine.dispose()


def test_statistics_uses_local_tracking_and_hides_incomplete_durations(tmp_path):
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
    assert incomplete.watched_movie_minutes is None
    assert incomplete.watched_episode_minutes is None
    assert incomplete.estimated_total_minutes is None
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
    from PySide6.QtCore import QObject
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
        dashboard = window.findChild(QQuickItem, "dashboardStats")
        for _ in range(100):
            application.processEvents()
            if (
                not statistics.busy
                and statistics.stats.get("watched_movies") == 1
                and dashboard.isVisible()
            ):
                break
            QTest.qWait(10)
        else:
            raise AssertionError("İstatistikler yüklenmedi")
        button = window.findChild(QQuickItem, "allStatisticsButton")
        assert dashboard is not None and dashboard.isVisible()
        for width, height in ((1366, 768), (1920, 1080)):
            window.resize(width, height)
            application.processEvents()
            assert dashboard.width() > 260 and dashboard.height() > 200
        button.forceActiveFocus()
        QTest.keyClick(window, " ")
        dialog = window.findChild(QObject, "statisticsDialog")
        assert dialog is not None and dialog.property("opened")
    finally:
        window.close()
        statistics.close()
        movie_library.close()
        tv_library.close()
        continuing.close()
        application.processEvents()
        engine.dispose()
