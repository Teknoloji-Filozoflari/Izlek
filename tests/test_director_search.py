"""Director discovery uses credited jobs, local exclusions and stale-request guards."""

from threading import Event, get_ident

import httpx
import pytest
from PySide6.QtCore import QPointF, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.services.content_visibility import ContentVisibilityService
from izlek.services.director_search import DirectorSearchService
from izlek.tmdb.client import NetworkError, TmdbClient
from izlek.tmdb.models import PersonMovieCredits, PersonSearchResults, PersonTvCredits
from izlek.ui.controllers.discover_controller import DiscoverController
from izlek.ui.controllers.movie_detail_controller import MovieDetailController
from izlek.ui.controllers.search_controller import SearchController
from izlek.ui.controllers.token_controller import TokenController
from test_discover import _DiscoverClient
from test_global_search import (
    ExistingTokenStore,
    FakeImages,
    FakeMovieService,
    find_visual,
    wait_for,
)


class DirectorClient:
    def __init__(self):
        self.calls = []
        self.threads = []
        self.entered = Event()
        self.release = Event()
        self.block = False
        self.offline = False

    def search_person(self, query):
        self.calls.append(("person", query))
        self.threads.append(get_ident())
        if self.offline:
            raise NetworkError("offline")
        if self.block:
            self.entered.set()
            assert self.release.wait(timeout=3)
        return PersonSearchResults.model_validate(
            {
                "page": 1,
                "total_pages": 1,
                "total_results": 2,
                "results": [
                    {"id": 2, "name": "Alex Actor", "known_for_department": "Acting"},
                    {
                        "id": 1,
                        "name": "Alex Director",
                        "known_for_department": "Directing",
                    },
                ],
            }
        )

    def person_movie_credits(self, person_id):
        self.calls.append(("movie", person_id))
        self.threads.append(get_ident())
        if self.offline:
            raise NetworkError("offline")
        return PersonMovieCredits.model_validate(
            {
                "id": person_id,
                "cast": [
                    {"id": 90, "title": "Acting Only", "original_title": "Acting Only"}
                ],
                "crew": [
                    {
                        "id": 10,
                        "title": "Eski",
                        "original_title": "Old Film",
                        "job": "Director",
                        "release_date": "2000-01-01",
                    },
                    {
                        "id": 11,
                        "title": "Yeni",
                        "original_title": "New Film",
                        "job": "Director",
                        "release_date": "2025-01-01",
                        "vote_average": 8.5,
                    },
                    {
                        "id": 11,
                        "title": "Yeni",
                        "original_title": "New Film",
                        "job": "Director",
                        "release_date": "2025-01-01",
                        "vote_average": 8.5,
                    },
                    {
                        "id": 12,
                        "title": "Writer",
                        "original_title": "Writer",
                        "job": "Writer",
                    },
                    {
                        "id": 13,
                        "title": "Assistant",
                        "original_title": "Assistant",
                        "job": "Assistant Director",
                    },
                    {
                        "id": 14,
                        "title": "Unknown",
                        "original_title": "Unknown",
                        "job": "Director",
                        "release_date": "",
                    },
                ],
            }
        )

    def person_tv_credits(self, person_id):
        self.calls.append(("tv", person_id))
        self.threads.append(get_ident())
        return PersonTvCredits.model_validate(
            {
                "id": person_id,
                "crew": [
                    {
                        "id": 10,
                        "name": "Dizi",
                        "original_name": "Original Show",
                        "job": "Director",
                        "first_air_date": "2024-01-01",
                    },
                    {
                        "id": 20,
                        "name": "Creator",
                        "original_name": "Creator",
                        "job": "Creator",
                    },
                ],
            }
        )


@pytest.mark.parametrize("kind", ["movie", "tv"])
def test_person_api_paths_and_typed_crew(kind):
    calls = []

    def respond(request):
        calls.append(request)
        if request.url.path.endswith("/search/person"):
            return httpx.Response(
                200,
                json={
                    "page": 1,
                    "total_pages": 1,
                    "total_results": 1,
                    "results": [{"id": 7, "name": "Director"}],
                },
            )
        return httpx.Response(200, json={"id": 7, "crew": []})

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        client = TmdbClient(http, token="test-only")
        assert client.search_person("Director").results[0].id == 7
        assert calls[0].url.params["include_adult"] == "false"
        assert calls[0].url.params["query"] == "Director"
        credits = getattr(client, f"person_{kind}_credits")(7)
        assert credits.crew == []
        assert calls[-1].url.path == f"/3/person/7/{kind}_credits"


def test_directing_jobs_only_deduplicated_with_original_titles():
    service = DirectorSearchService(DirectorClient())
    assert [row["id"] for row in service.search("Alex")] == [1, 2]
    assert [row.id for row in service.works(1, "movie")] == [11, 10, 14]
    assert [row.original_name for row in service.works(1, "tv")] == ["Original Show"]


def test_director_results_hide_saved_media_and_refresh_without_network(tmp_path):
    app = QGuiApplication.instance() or QGuiApplication([])
    db = initialize_database(tmp_path / "director.sqlite3")
    factory = create_session_factory(db)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(10, MediaType.MOVIE, "Saved")
        UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHED)
    client = DirectorClient()
    search = SearchController(
        client=client, images=FakeImages(), visibility=ContentVisibilityService(factory)
    )
    try:
        search.searchDirectors("Alex")
        wait_for(app, lambda: bool(search.directors) and not search.busy)
        search.selectDirector(1, "movie")
        wait_for(app, lambda: bool(search.movies) and not search.busy)
        assert [row["id"] for row in search.movies] == [11, 14]
        assert search.movies[0]["title"] == "New Film"
        assert search.movies[0]["score"] == 8.5
        with factory.begin() as session:
            media = MediaRepository(session).upsert(11, MediaType.MOVIE, "New Film")
            UserMediaRepository(session).set_favorite(media.id, True)
        search.refresh_visibility()
        wait_for(app, lambda: len(search.movies) == 1)
        assert client.calls == [("person", "Alex"), ("movie", 1)]
        search.selectDirector(1, "tv")
        wait_for(app, lambda: bool(search.shows) and not search.busy)
        assert search.shows[0]["id"] == 10
        assert search.movies == []
        assert all(thread != get_ident() for thread in client.threads)
    finally:
        search.close()
        db.dispose()


def test_director_search_rejects_late_people_after_clear():
    app = QGuiApplication.instance() or QGuiApplication([])
    client = DirectorClient()
    client.block = True
    search = SearchController(client=client, images=FakeImages())
    try:
        search.searchDirectors("Alex")
        assert client.entered.wait(timeout=1)
        search.clear()
        generation = search._generation
        client.release.set()
        search._apply_directors(generation - 1, [{"id": 99, "name": "Stale"}], "")
        app.processEvents()
        assert search.directors == [] and not search.busy
        assert search.selectedDirector == {}
    finally:
        client.release.set()
        search.close()


def test_director_errors_recover_and_short_queries_do_not_request(initialized_factory):
    app = QGuiApplication.instance() or QGuiApplication([])
    client = DirectorClient()
    search = SearchController(
        client=client,
        images=FakeImages(),
        visibility=ContentVisibilityService(initialized_factory),
    )
    try:
        search.searchDirectors("Al")
        assert client.calls == []
        client.offline = True
        search.searchDirectors("Alex")
        wait_for(app, lambda: bool(search.error) and not search.busy)
        client.offline = False
        search.searchDirectors("Alex")
        wait_for(app, lambda: bool(search.directors) and not search.busy)
        client.offline = True
        search.selectDirector(1, "movie")
        wait_for(app, lambda: bool(search.error) and not search.busy)
        assert search.selectedDirector["id"] == 1
        client.offline = False
        search.selectDirector(1, "movie")
        wait_for(app, lambda: bool(search.movies) and not search.busy)
        assert not search.error
    finally:
        search.close()


def test_discover_director_mode_selection_switch_category_and_detail(tmp_path):
    search = SearchController(client=DirectorClient(), images=FakeImages())
    discover = DiscoverController(client=_DiscoverClient(), images=FakeImages())
    movie = MovieDetailController(FakeMovieService(), FakeImages())
    warnings = []

    def collect(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous = qInstallMessageHandler(collect)
    app, engine, window = create_application(
        token_controller=TokenController(store=ExistingTokenStore()),
        search_controller=search,
        discover_controller=discover,
        movie_controller=movie,
    )
    try:
        window.resize(1366, 768)
        mode = window.findChild(QQuickItem, "discoverSearchMode")
        mode.selected.emit(1)
        field = window.findChild(QQuickItem, "dashboardSearch")
        assert "Yönetmen" in field.property("placeholderText")
        field.setProperty("text", "Alex")
        wait_for(app, lambda: len(search.directors) == 2 and not search.busy)
        people = window.findChild(QQuickItem, "directorSearchResults")
        option = find_visual(people, "directorSearchOption")
        option.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        wait_for(app, lambda: bool(search.movies) and not search.busy)
        assert search.selectedDirector["id"] == 1
        selector = window.findChild(QQuickItem, "discoverMedia")
        selector.setProperty("currentIndex", 1)
        selector.activated.emit(1)
        wait_for(app, lambda: bool(search.shows) and not search.busy)
        assert search.shows[0]["title"] == "Original Show"
        selector.setProperty("currentIndex", 0)
        selector.activated.emit(0)
        wait_for(app, lambda: bool(search.movies) and not search.busy)
        grid = window.findChild(QQuickItem, "discoverResults")
        for width, height in ((850, 768), (1366, 768), (1920, 1080)):
            window.resize(width, height)
            app.processEvents()
            assert field.width() > 100 and grid.width() > 0
        card = grid.property("currentItem")
        point = card.mapToScene(QPointF(card.width() / 2, card.height() / 2))
        QTest.mouseClick(
            window,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            point.toPoint(),
        )
        wait_for(app, lambda: movie.detail.get("title") == "Original Detail")
        QTest.keyClick(window, Qt.Key.Key_Escape)
        wait_for(
            app,
            lambda: window.findChild(QQuickItem, "contentStack").property("depth") == 1,
        )
        assert field.property("text") == "Alex"
        assert search.selectedDirector["id"] == 1
        mode.selected.emit(0)
        assert not search.directors and not search.selectedDirector
        assert not warnings
    finally:
        window.close()
        search.close()
        movie.close()
        discover.close()
        app.processEvents()
        qInstallMessageHandler(previous)
