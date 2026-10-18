"""Actor navigation and reversible filmography visibility for both person roles."""

from threading import Event

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
from izlek.services.custom_lists import CustomListsService
from izlek.services.director_search import DirectorSearchService
from izlek.services.movie_detail import MovieDetailService
from izlek.services.tv_detail import TvDetailService
from izlek.tmdb.client import TmdbClient
from izlek.tmdb.models import PersonMovieCredits, PersonSearchResults, PersonTvCredits
from izlek.ui.controllers.discover_controller import DiscoverController
from izlek.ui.controllers.movie_detail_controller import MovieDetailController
from izlek.ui.controllers.search_controller import SearchController
from izlek.ui.controllers.token_controller import TokenController
from izlek.ui.controllers.tv_detail_controller import TvDetailController
from test_discover import _DiscoverClient
from test_global_search import ExistingTokenStore, FakeImages, find_visual, wait_for
from test_movie_detail import responses
from test_tv_detail import FakeImages as DetailImages
from test_tv_detail import payloads


class PersonClient:
    def __init__(self):
        self.calls = []
        self.block_movie = False
        self.entered = Event()
        self.release = Event()

    def search_person(self, query):
        self.calls.append(("person", query))
        return PersonSearchResults.model_validate(
            {
                "page": 1,
                "total_pages": 1,
                "total_results": 2,
                "results": [
                    {"id": 1, "name": "Person", "known_for_department": "Directing"},
                    {"id": 3, "name": "Actor", "known_for_department": "Acting"},
                ],
            }
        )

    def _credits(self, person_id, kind):
        self.calls.append((kind, person_id))
        if kind == "movie" and self.block_movie:
            self.entered.set()
            assert self.release.wait(timeout=3)
        rows = [
            {
                "id": item_id,
                "title": f"Film {item_id}",
                "original_title": f"Film {item_id}",
                "name": f"Show {item_id}",
                "original_name": f"Show {item_id}",
                "release_date": f"20{item_id}-01-01",
                "first_air_date": f"20{item_id}-01-01",
                "poster_path": "/poster.jpg",
                "vote_average": 8.0,
            }
            for item_id in range(10, 17)
        ]
        schema = PersonMovieCredits if kind == "movie" else PersonTvCredits
        return schema.model_validate(
            {
                "id": person_id,
                "cast": rows + [rows[0]],
                "crew": [{**row, "job": "Director"} for row in rows]
                + [{**rows[0], "id": 99, "job": "Producer"}],
            }
        )

    def person_movie_credits(self, person_id):
        return self._credits(person_id, "movie")

    def person_tv_credits(self, person_id):
        return self._credits(person_id, "tv")


@pytest.fixture
def person_factory(tmp_path):
    engine = initialize_database(tmp_path / "people.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        for kind in MediaType:
            for item_id in range(10, 17):
                media = MediaRepository(session).upsert(
                    item_id, kind, f"Saved {item_id}"
                )
                if item_id < 13:
                    status = [
                        TrackingStatus.WATCHED,
                        TrackingStatus.WATCHING,
                        TrackingStatus.PLANNED,
                    ][item_id - 10]
                    UserMediaRepository(session).set_status(media.id, status)
                elif item_id == 13:
                    UserMediaRepository(session).set_favorite(media.id, True)
    lists = CustomListsService(factory)
    list_id = lists.create("Listed")
    lists.add_many(list_id, [{"kind": kind, "tmdb_id": 14} for kind in ("movie", "tv")])
    try:
        yield factory
    finally:
        engine.dispose()


def test_actor_uses_cast_and_role_priority_for_both_categories():
    service = DirectorSearchService(PersonClient())
    assert service.search("Person", "actor")[0]["id"] == 3
    for kind in ("movie", "tv"):
        works = service.works(3, kind, "actor")
        assert [row.id for row in works] == list(range(16, 9, -1))
        assert all(row.id != 99 for row in works)


@pytest.mark.parametrize("kind", ["movie", "tv"])
@pytest.mark.parametrize("role", ["actor", "director"])
def test_person_scope_is_reversible_local_and_updates_badges(
    person_factory, kind, role
):
    app = QGuiApplication.instance() or QGuiApplication([])
    client = PersonClient()
    search = SearchController(
        client=client,
        images=FakeImages(),
        visibility=ContentVisibilityService(person_factory),
    )
    try:
        search.searchPeople("Person", role)
        wait_for(app, lambda: bool(search.people) and not search.busy)
        search.selectPerson(3 if role == "actor" else 1, kind, role)
        wait_for(app, lambda: not search.busy and bool(search.movies or search.shows))

        def rows():
            return search.movies if kind == "movie" else search.shows

        assert not search.includeSaved
        assert [row["id"] for row in rows()] == [16, 15]
        calls = list(client.calls)
        search.setIncludeSaved(True)
        assert [row["id"] for row in rows()] == list(range(16, 9, -1))
        states = {row["id"]: row["status"] for row in rows()}
        assert states == {
            10: "WATCHED",
            11: "WATCHING",
            12: "PLANNED",
            13: "SAVED",
            14: "SAVED",
            15: "",
            16: "",
        }
        with person_factory.begin() as session:
            media = MediaRepository(session).get_by_tmdb(15, MediaType(kind.upper()))
            UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHED)
        search.refresh_visibility()
        wait_for(
            app,
            lambda: (
                next(row for row in rows() if row["id"] == 15)["status"] == "WATCHED"
            ),
        )
        assert len(rows()) == 7
        search.setIncludeSaved(False)
        assert [row["id"] for row in rows()] == [16]
        search.setIncludeSaved(True)
        assert len(rows()) == 7 and all(row["poster"] for row in rows())
        assert client.calls == calls
        other = "tv" if kind == "movie" else "movie"
        search.selectPerson(search.selectedPerson["id"], other, role)
        wait_for(app, lambda: not search.busy)
        assert search.includeSaved
        assert len(search.shows if other == "tv" else search.movies) == 7
        search.clear()
        assert not search.includeSaved and not search.selectedPerson
    finally:
        search.close()


def test_actor_navigation_uses_exact_id_and_rejects_old_credits(person_factory):
    app = QGuiApplication.instance() or QGuiApplication([])
    client = PersonClient()
    client.block_movie = True
    search = SearchController(
        client=client,
        images=FakeImages(),
        visibility=ContentVisibilityService(person_factory),
    )
    try:
        search.openActor(3, "Li", "movie")
        assert client.entered.wait(timeout=1)
        old_request = search._futures[0]
        search.selectPerson(3, "tv", "actor")
        wait_for(app, lambda: not search.busy and bool(search.shows))
        search.setIncludeSaved(True)
        client.release.set()
        old_request.result(timeout=2)
        app.processEvents()
        assert search.movies == [] and len(search.shows) == 7
        assert search.selectedPerson == {"id": 3, "name": "Li"}
        assert not any(call[0] == "person" for call in client.calls)
    finally:
        client.release.set()
        search.close()


@pytest.mark.parametrize("kind", ["movie", "tv"])
def test_cast_click_opens_actor_discovery_and_scope_preserves_return(
    person_factory, kind
):
    client = PersonClient()
    search = SearchController(
        client=client,
        images=FakeImages(),
        visibility=ContentVisibilityService(person_factory),
    )
    discover = DiscoverController(client=_DiscoverClient(), images=FakeImages())
    data = responses() if kind == "movie" else payloads()
    detail_id = 42 if kind == "movie" else 77
    warnings = []

    def collect(level, context, message):
        if level in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous = qInstallMessageHandler(collect)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=data[request.url.path])
        )
    ) as http:
        service_type = MovieDetailService if kind == "movie" else TvDetailService
        service = service_type(TmdbClient(http, token="test-only"), person_factory)
        service.load(detail_id)
        controller_type = (
            MovieDetailController if kind == "movie" else TvDetailController
        )
        detail = controller_type(service, images=DetailImages())
        app, engine, window = create_application(
            token_controller=TokenController(store=ExistingTokenStore()),
            search_controller=search,
            discover_controller=discover,
            **{f"{kind}_controller": detail},
        )
        try:
            window.resize(1366, 768)
            window.openMediaDetail(kind, detail_id)
            wait_for(app, lambda: not detail.busy and bool(detail.detail.get("cast")))
            person = detail.detail["cast"][0]
            assert person["id"] > 0
            cast = window.findChild(QQuickItem, f"{kind}CastGrid")
            card = find_visual(cast, "castActorCard")
            scroll = window.findChild(QQuickItem, f"{kind}DetailScroll")
            flickable = scroll.property("contentItem")
            point = card.mapToItem(flickable, QPointF(0, 0))
            flickable.setProperty(
                "contentY", flickable.property("contentY") + point.y() - 30
            )
            app.processEvents()
            point = card.mapToScene(QPointF(card.width() / 2, card.height() / 2))
            QTest.mouseClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                point.toPoint(),
            )
            wait_for(
                app, lambda: not search.busy and bool(search.movies or search.shows)
            )
            stack = window.findChild(QQuickItem, "contentStack")
            assert stack.property("depth") == 1
            assert stack.property("currentItem").property("searchMode") == "actor"
            assert window.property("currentIndex") == 0
            assert search.selectedPerson["id"] == person["id"]
            assert client.calls == [(kind, person["id"])]
            scope = window.findChild(QQuickItem, "personResultsScope")
            scope.selected.emit(1)
            grid = window.findChild(QQuickItem, "discoverResults")
            assert grid.property("count") == 7
            grid.setProperty("currentIndex", 6)
            app.processEvents()
            badge = find_visual(grid.property("currentItem"), "cardStatus")
            assert badge.property("text") == "İzlendi"
            assert search.includeSaved
            window.openMediaDetail(kind, detail_id)
            wait_for(app, lambda: not detail.busy)
            window.goBack()
            assert stack.property("depth") == 1
            assert search.includeSaved and grid.property("count") == 7
            assert scope.property("currentIndex") == 1
            scope.selected.emit(0)
            assert grid.property("count") == 2
            field = window.findChild(QQuickItem, "dashboardSearch")
            for width, height in ((850, 768), (1366, 768), (1920, 1080)):
                window.resize(width, height)
                app.processEvents()
                assert field.width() > 100
            window.findChild(QQuickItem, "changeDirectorButton").clicked.emit()
            wait_for(app, lambda: bool(search.people) and not search.busy)
            assert search.people[0]["id"] == 3
            people_view = window.findChild(QQuickItem, "directorSearchResults")
            option = find_visual(people_view, "directorSearchOption")
            option.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Space)
            wait_for(
                app, lambda: not search.busy and bool(search.movies or search.shows)
            )
            assert search.selectedPerson["id"] == 3 and not search.includeSaved
            assert not warnings
        finally:
            window.close()
            for child in engine.children():
                if callable(getattr(child, "close", None)):
                    child.close()
            app.processEvents()
            qInstallMessageHandler(previous)
