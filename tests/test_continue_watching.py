"""Local Continue Watching selection and quick action behavior."""

from concurrent.futures import Future
from datetime import date, timedelta
from pathlib import Path
from threading import Event, get_ident

import pytest
from PySide6.QtCore import Qt
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
from izlek.services.continue_watching import (
    ContinueWatchingItem,
    ContinueWatchingService,
)
from izlek.services.tv_detail import TvDetailService
from izlek.tmdb.client import TmdbClient
from izlek.ui.controllers.continue_watching_controller import ContinueWatchingController
from izlek.ui.controllers.token_controller import TokenController
from test_tv_detail import FakeImages, wait_for


def test_continue_keyring_load_does_not_block_ui_thread(monkeypatch):
    app = QGuiApplication.instance() or QGuiApplication([])
    entered, release = Event(), Event()
    caller = get_ident()

    class Images(FakeImages):
        def close(self):
            pass

    module = "izlek.ui.controllers.continue_watching_controller"
    monkeypatch.setattr(f"{module}.TmdbClient", lambda **kwargs: object())
    monkeypatch.setattr(f"{module}.ImageService", lambda client: Images())

    class Store:
        def load(self):
            assert get_ident() != caller
            entered.set()
            assert release.wait(timeout=2)
            return None

    class Service:
        def list_next(self):
            return [ContinueWatchingItem(42, "Show", "", "", 1, 1, "Pilot", 0, 1)]

        def close(self):
            pass

    controller = ContinueWatchingController(service=Service(), store=Store())
    try:
        controller.refresh()
        assert entered.wait(timeout=1)
        app.processEvents()
        assert controller.busy
        release.set()
        wait_for(app, lambda: not controller.busy)
        assert controller.items[0]["episodeCode"] == "S01E01"
    finally:
        release.set()
        controller.close()


@pytest.mark.parametrize("status", [None, *TrackingStatus])
@pytest.mark.parametrize("has_progress", [False, True])
def test_continue_requires_library_membership_even_with_favorites_and_progress(
    tmp_path, status, has_progress
):
    engine = initialize_database(tmp_path / "membership.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(42, MediaType.TV, "Show")
        users = UserMediaRepository(session)
        users.set_status(media.id, status)
        users.set_favorite(media.id, True)
        season = SeasonRepository(session).upsert(media.id, 1)
        episodes = EpisodeRepository(session)
        episode = episodes.upsert(season.id, 1, air_date=date(2020, 1, 1))
        if has_progress:
            episodes.set_watched(episode.id, False)
    try:
        items = ContinueWatchingService(factory).list_next()
        expected = status is not None and (
            status == TrackingStatus.WATCHING or has_progress
        )
        assert bool(items) == expected
    finally:
        engine.dispose()


def test_removed_show_leaves_continue_and_readd_preserves_next_episode(tmp_path):
    engine = initialize_database(tmp_path / "remove.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(42, MediaType.TV, "Show")
        users = UserMediaRepository(session)
        users.set_status(media.id, TrackingStatus.WATCHING)
        users.set_favorite(media.id, True)
        season = SeasonRepository(session).upsert(media.id, 1)
        episodes = EpisodeRepository(session)
        first = episodes.upsert(season.id, 1, air_date=date(2020, 1, 1))
        second = episodes.upsert(season.id, 2, air_date=date(2020, 1, 2))
        episodes.set_watched(first.id, True)
        media_id, first_id, second_id = media.id, first.id, second.id
    service = ContinueWatchingService(factory)
    tv = TvDetailService(TmdbClient(), factory)
    try:
        assert service.list_next()[0].episode_number == 2
        tv.set_status(42, None)
        assert service.list_next() == []
        with pytest.raises(LookupError, match="kütüphanede"):
            tv.set_episode_watched(42, 1, 2, True, require_in_library=True)
        with factory() as session:
            user = UserMediaRepository(session).get(media_id)
            assert user.status is None and user.favorite
            assert EpisodeRepository(session).get_progress(first_id).watched
            assert EpisodeRepository(session).get_progress(second_id) is None
        tv.set_status(42, "WATCHING")
        assert service.list_next()[0].episode_number == 2
    finally:
        tv.close()
        service.close()
        engine.dispose()


@pytest.mark.parametrize("season_number, air_date", [
    (0, date(2020, 1, 1)), (1, None), (1, date.today() + timedelta(days=1)),
])
def test_continue_action_rejects_special_undated_and_future_episodes(
    tmp_path, season_number, air_date
):
    engine = initialize_database(tmp_path / "invalid-episode.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(42, MediaType.TV, "Show")
        UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHING)
        season = SeasonRepository(session).upsert(media.id, season_number)
        episode = EpisodeRepository(session).upsert(season.id, 1, air_date=air_date)
        episode_id = episode.id
    tv = TvDetailService(TmdbClient(), factory)
    try:
        with pytest.raises(ValueError, match="yayınlanmış"):
            tv.set_episode_watched(
                42, season_number, 1, True, require_in_library=True
            )
        with factory() as session:
            assert EpisodeRepository(session).get_progress(episode_id) is None
    finally:
        tv.close()
        engine.dispose()


def test_continue_write_survives_refresh_and_rejects_double_clicks(tmp_path):
    app = QGuiApplication.instance() or QGuiApplication([])
    engine = initialize_database(tmp_path / "writes.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(42, MediaType.TV, "Show")
        UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHING)
        season = SeasonRepository(session).upsert(media.id, 1)
        episode = EpisodeRepository(session).upsert(
            season.id, 1, air_date=date(2020, 1, 1)
        )
        episode_id = episode.id
    entered, release = Event(), Event()
    calls, saved = [], []

    class BlockingTv:
        def set_episode_watched(self, *args, **kwargs):
            calls.append(args)
            assert kwargs == {"require_in_library": True}
            entered.set()
            assert release.wait(timeout=2)
            with factory.begin() as session:
                EpisodeRepository(session).set_watched(episode_id, True)

        def close(self):
            pass

    controller = ContinueWatchingController(
        ContinueWatchingService(factory), BlockingTv(), FakeImages()
    )
    controller.progressSaved.connect(lambda: saved.append(True))
    try:
        controller.refresh()
        wait_for(app, lambda: not controller.busy)
        controller.markWatched(999, 1, 1)
        assert not calls and not controller.busy
        controller.markWatched(42, 1, 1)
        assert entered.wait(timeout=1)
        controller.markWatched(42, 1, 1)
        controller.refresh()
        controller.refresh()
        release.set()
        wait_for(app, lambda: not controller.busy and bool(saved))
        assert len(calls) == 1
        assert saved == [True]
        assert controller.items == []
    finally:
        release.set()
        controller.close()
        engine.dispose()


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
        UserMediaRepository(session).set_status(eligible.id, TrackingStatus.PLANNED)
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


def test_continue_list_is_not_limited_to_two_shows(tmp_path):
    engine = initialize_database(tmp_path / "izlek.sqlite3")
    factory = create_session_factory(engine)
    today = date(2026, 10, 3)
    with factory.begin() as session:
        for tmdb_id in (31, 32, 33):
            media = MediaRepository(session).upsert(tmdb_id, MediaType.TV, "Show")
            UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHING)
            season = SeasonRepository(session).upsert(media.id, 1)
            EpisodeRepository(session).upsert(season.id, 1, air_date=today)
    try:
        items = ContinueWatchingService(factory).list_next(today=today)
        assert {item.tmdb_id for item in items} == {31, 32, 33}
    finally:
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
        def set_episode_watched(
            self, tv_id, season_number, episode_number, watched, *, require_in_library
        ):
            assert require_in_library
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
        assert window.findChild(QQuickItem, "dashboardSearch") is not None
        window.navigate(4)
        assert window.findChild(QQuickItem, "dashboardStats").isVisible()
        assert window.findChild(QQuickItem, "showsContinueSection") is None
        window.navigate(2)
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
        assert window.findChild(QQuickItem, "showsContinueSection").isVisible()

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
        button.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
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
