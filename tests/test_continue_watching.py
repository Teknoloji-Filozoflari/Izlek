"""Local Continue Watching selection and quick action behavior."""

from concurrent.futures import Future
from datetime import date
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

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
from izlek.ui.controllers.continue_watching_controller import ContinueWatchingController
from izlek.ui.controllers.token_controller import TokenController


def test_next_episode_filters_special_undated_future_and_completed(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    today = date(2026, 10, 3)
    with factory.begin() as session:
        media = MediaRepository(session)
        seasons = SeasonRepository(session)
        episodes = EpisodeRepository(session)
        users = UserMediaRepository(session)
        show = media.upsert(1, MediaType.TV, "First Show", poster_path="/a.jpg")
        users.set_status(show.id, TrackingStatus.WATCHING)
        special = seasons.upsert(show.id, 0)
        special_ep = episodes.upsert(special.id, 1, air_date=today)
        episodes.set_watched(special_ep.id, True)
        first = seasons.upsert(show.id, 1)
        watched = episodes.upsert(first.id, 1, air_date=today)
        episodes.set_watched(watched.id, True)
        episodes.upsert(first.id, 2, air_date=None)
        episodes.upsert(first.id, 3, air_date=date(2027, 1, 1))
        second = seasons.upsert(show.id, 2)
        episodes.upsert(second.id, 1, name="Next Season", air_date=today)
        # A repeat upsert must not create a second card or change order.
        episodes.upsert(second.id, 1, name="Next Season", air_date=today)

        complete = media.upsert(2, MediaType.TV, "Completed")
        complete_season = seasons.upsert(complete.id, 1)
        complete_ep = episodes.upsert(complete_season.id, 1, air_date=today)
        episodes.set_watched(complete_ep.id, True)

        movie = media.upsert(3, MediaType.MOVIE, "Movie")
        users.set_status(movie.id, TrackingStatus.WATCHING)
        planned = media.upsert(4, MediaType.TV, "Planned")
        planned_season = seasons.upsert(planned.id, 1)
        episodes.upsert(planned_season.id, 1, air_date=today)
        users.set_status(planned.id, TrackingStatus.PLANNED)

    service = ContinueWatchingService(factory)
    items = service.list_next(today=today)
    assert len(items) == 1
    assert items[0].tmdb_id == 1
    assert (items[0].season_number, items[0].episode_number) == (2, 1)
    assert items[0].episode_title == "Next Season"
    assert (items[0].watched_count, items[0].aired_count) == (1, 2)
    assert items[0].poster_path == "/a.jpg"
    engine.dispose()


def test_watching_without_progress_uses_first_released_episode(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    today = date(2026, 10, 3)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(8, MediaType.TV, "Started")
        UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHING)
        season = SeasonRepository(session).upsert(media.id, 1)
        repo = EpisodeRepository(session)
        repo.upsert(season.id, 1, air_date=None)
        repo.upsert(season.id, 2, air_date=today)
    items = ContinueWatchingService(factory).list_next(today=today)
    assert [(item.tmdb_id, item.episode_number) for item in items] == [(8, 2)]
    engine.dispose()


def test_progress_row_qualifies_but_special_progress_does_not(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    today = date(2026, 10, 3)
    with factory.begin() as session:
        media = MediaRepository(session)
        seasons = SeasonRepository(session)
        episodes = EpisodeRepository(session)
        eligible = media.upsert(11, MediaType.TV, "Unwatched progress")
        regular = seasons.upsert(eligible.id, 1)
        episode = episodes.upsert(regular.id, 1, air_date=today)
        episodes.set_watched(episode.id, False)
        special_only = media.upsert(12, MediaType.TV, "Special only")
        special = seasons.upsert(special_only.id, 0)
        special_episode = episodes.upsert(special.id, 1, air_date=today)
        episodes.set_watched(special_episode.id, True)
        regular = seasons.upsert(special_only.id, 1)
        episodes.upsert(regular.id, 1, air_date=today)
    items = ContinueWatchingService(factory).list_next(today=today)
    assert [item.tmdb_id for item in items] == [11]
    engine.dispose()


def test_completed_show_with_new_released_episode_returns_to_continue(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    today = date(2026, 10, 3)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(21, MediaType.TV, "Returning Show")
        UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHED)
        season = SeasonRepository(session).upsert(media.id, 1)
        episodes = EpisodeRepository(session)
        watched = episodes.upsert(season.id, 1, air_date=date(2025, 1, 1))
        episodes.set_watched(watched.id, True)
        episodes.upsert(season.id, 2, name="New episode", air_date=today)

    try:
        items = ContinueWatchingService(factory).list_next(today=today)
        assert [(item.tmdb_id, item.episode_number) for item in items] == [(21, 2)]
    finally:
        engine.dispose()


def test_home_card_quick_action_and_layout(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = QGuiApplication.instance() or QGuiApplication([])
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(10, MediaType.TV, "Home Show")
        UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHING)
        season = SeasonRepository(session).upsert(media.id, 1)
        EpisodeRepository(session).upsert(
            season.id, 1, name="Pilot", air_date=date(2020, 1, 1)
        )

    class Store:
        def load(self):
            return StoredToken("test-only", "keyring")

    class Images:
        def poster(self, path):
            future = Future()
            future.set_result(
                Path(__file__).resolve().parents[1]
                / "src/izlek/resources/images/poster-placeholder.svg"
            )
            return future

        def backdrop(self, path):
            return self.poster(path)

    class TvService:
        def set_episode_watched(self, tv_id, season_number, episode_number, watched):
            with factory.begin() as session:
                media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
                season = SeasonRepository(session).list_for_media(media.id)[0]
                episode = EpisodeRepository(session).list_for_season(season.id)[0]
                EpisodeRepository(session).set_watched(episode.id, watched)

        def close(self):
            pass

    continuing = ContinueWatchingController(
        service=ContinueWatchingService(factory),
        tv_service=TvService(),
        images=Images(),
    )
    token = TokenController(store=Store())
    app, qml_engine, window = create_application(
        token_controller=token, continue_controller=continuing
    )
    try:
        for _ in range(100):
            app.processEvents()
            if continuing.items and not continuing.busy:
                break
            QTest.qWait(10)
        assert continuing.items[0]["episodeCode"] == "S01E01"
        for width, height in ((1366, 768), (1920, 1080)):
            window.resize(width, height)
            app.processEvents()
            assert window.width() == width and window.height() == height
        current = window.findChild(QQuickItem, "contentStack").property("currentItem")
        assert window.findChild(QQuickItem, "dashboardSearch") is not None
        assert window.findChild(QQuickItem, "dashboardQuickEntry") is not None
        stats = window.findChild(QQuickItem, "dashboardStats")
        assert stats is not None and stats.isVisible()

        def find_card(item):
            if item.objectName() == "continueCard":
                return item
            for child in item.childItems():
                found = find_card(child)
                if found is not None:
                    return found
            return None

        card = find_card(current)
        assert card is not None and card.isVisible()
        button = next(
            child
            for child in card.findChildren(QQuickItem)
            if child.objectName() == "continueWatchedButton"
        )
        center = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
        QTest.mouseClick(
            window,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(int(center.x()), int(center.y())),
        )
        for _ in range(100):
            app.processEvents()
            if not continuing.busy:
                break
            QTest.qWait(10)
        assert continuing.items == []
    finally:
        window.close()
        continuing.close()
        app.processEvents()
        engine.dispose()
