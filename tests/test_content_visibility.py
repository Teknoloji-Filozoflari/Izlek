"""Personal result exclusions, recommendation history and list status."""

import httpx
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import (
    CustomListRepository,
    EpisodeRepository,
    MediaRepository,
    SeasonRepository,
    UserMediaRepository,
)
from izlek.services.content_visibility import ContentVisibilityService
from izlek.services.custom_lists import CustomListsService
from izlek.services.movie_detail import MovieDetailService
from izlek.services.tv_detail import TvDetailService
from izlek.tmdb.client import TmdbClient
from izlek.tmdb.models import MovieSearchResults, TvSearchResults
from izlek.ui.controllers.movie_detail_controller import MovieDetailController
from izlek.ui.controllers.search_controller import SearchController
from izlek.ui.controllers.token_controller import TokenController
from izlek.ui.controllers.tv_detail_controller import TvDetailController
from test_global_search import ExistingTokenStore, FakeImages, wait_for
from test_movie_detail import responses
from test_tv_detail import FakeImages as DetailImages
from test_tv_detail import payloads


@pytest.fixture
def local_factory(tmp_path):
    engine = initialize_database(tmp_path / "personal.sqlite3")
    try:
        yield create_session_factory(engine)
    finally:
        engine.dispose()


def test_search_hides_personal_saves_but_not_cached_metadata(local_factory):
    with local_factory.begin() as session:
        repo = MediaRepository(session)
        users = UserMediaRepository(session)
        for item_id, status in enumerate(TrackingStatus, start=1):
            movie = repo.upsert(item_id, MediaType.MOVIE, str(item_id))
            users.set_status(movie.id, status)
        favorite = repo.upsert(4, MediaType.MOVIE, "Favorite only")
        users.set_favorite(favorite.id, True)
        listed = repo.upsert(5, MediaType.MOVIE, "Listed only")
        lists = CustomListRepository(session)
        custom_list = lists.create("Saved")
        lists.add_item(custom_list.id, listed.id)
        show = repo.upsert(6, MediaType.TV, "Progress without status")
        season = SeasonRepository(session).upsert(show.id, 1)
        episode = EpisodeRepository(session).upsert(season.id, 1)
        EpisodeRepository(session).set_watched(episode.id, True)
        repo.upsert(7, MediaType.MOVIE, "Metadata only")
        repo.upsert(1, MediaType.TV, "Same ID, different media type")
    visibility = ContentVisibilityService(local_factory)
    assert visibility.excluded_ids("movie") == {1, 2, 3, 4, 5}
    assert visibility.excluded_ids("tv") == {6}

    class Client:
        calls = []

        def search_movie(self, query):
            self.calls.append(("movie", query))
            return MovieSearchResults.model_validate({
                "page": 1, "total_pages": 1, "total_results": 7,
                "results": [
                    {"id": i, "title": str(i), "original_title": str(i)}
                    for i in range(1, 8)
                ],
            })

        def search_tv(self, query):
            self.calls.append(("tv", query))
            return TvSearchResults.model_validate({
                "page": 1, "total_pages": 1, "total_results": 2,
                "results": [
                    {"id": i, "name": str(i), "original_name": str(i)}
                    for i in (1, 6)
                ],
            })

    app = QGuiApplication.instance() or QGuiApplication([])
    client = Client()
    controller = SearchController(
        client=client, images=FakeImages(), visibility=visibility
    )
    try:
        controller.search("query")
        wait_for(app, lambda: not controller.busy)
        assert [item["id"] for item in controller.movies] == [6, 7]
        assert [item["id"] for item in controller.shows] == [1]
        with local_factory.begin() as session:
            movie = MediaRepository(session).get_by_tmdb(7, MediaType.MOVIE)
            UserMediaRepository(session).set_status(movie.id, TrackingStatus.PLANNED)
        controller.refresh_visibility()
        wait_for(app, lambda: len(controller.movies) == 1)
        assert controller.movies[0]["id"] == 6
        assert len(client.calls) == 2  # Local refresh does not repeat HTTP search.
        # A result queued before a save must also respect the new exclusions.
        controller._apply_search(
            controller._generation, "movie", [{"id": 7, "posterPath": ""}], ""
        )
        assert controller.movies == []
    finally:
        controller.close()


@pytest.mark.parametrize("kind", [MediaType.MOVIE, MediaType.TV])
def test_watched_recommendations_are_filtered_before_limit(local_factory, kind):
    is_movie = kind == MediaType.MOVIE
    item_id = 42 if is_movie else 77
    data = responses() if is_movie else payloads()
    section = data[f"/3/{kind.value.lower()}/{item_id}/recommendations"]
    section["results"] = [
        {"id": i, "title": str(i), "original_title": str(i),
         "name": str(i), "original_name": str(i)}
        for i in range(100, 112)
    ]
    section["total_results"] = 12
    with local_factory.begin() as session:
        repo = MediaRepository(session)
        users = UserMediaRepository(session)
        for rec_id in range(100, 109):
            media = repo.upsert(rec_id, kind, str(rec_id))
            users.set_status(media.id, TrackingStatus.WATCHED)
        planned = repo.upsert(109, kind, "Planned")
        users.set_status(planned.id, TrackingStatus.PLANNED)
        other_kind = MediaType.TV if is_movie else MediaType.MOVIE
        other = repo.upsert(110, other_kind, "Different type")
        users.set_status(other.id, TrackingStatus.WATCHED)
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=data[request.url.path])
    )) as http:
        service_type = MovieDetailService if is_movie else TvDetailService
        service = service_type(TmdbClient(http, token="test-only"), local_factory)
        detail = service.load(item_id)
        assert [row["id"] for row in detail["recommendations"]] == [109, 110, 111]
        with local_factory.begin() as session:
            media = MediaRepository(session).get_by_tmdb(109, kind)
            UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHED)
        assert [row["id"] for row in service.cached(item_id)["recommendations"]] == [
            110, 111
        ]
        with local_factory() as session:
            media = MediaRepository(session).get_by_tmdb(item_id, kind)
            assert len(media.metadata_json["recommendations"]["results"]) == 12


@pytest.mark.parametrize("first,next_kind", [
    ("movie", "movie"), ("tv", "tv"), ("movie", "tv"), ("tv", "movie")
])
def test_recommendations_back_returns_to_previous_identity(
    monkeypatch, first, next_kind,
):
    app, engine, window = create_application(
        token_controller=TokenController(store=ExistingTokenStore())
    )
    calls = []
    for kind, method in (("movie", "loadMovie"), ("tv", "loadTv")):
        controller = engine.rootContext().contextProperty(kind + "Controller")
        monkeypatch.setattr(
            controller, method, lambda item_id, k=kind: calls.append((k, item_id))
        )
    stack = window.findChild(QQuickItem, "contentStack")
    try:
        window.openMediaDetail(first, 1)
        page = stack.property("currentItem")
        selected = page.movieSelected if first == "movie" else page.tvSelected
        # Same-kind recommendations exercise the actual page signal.
        if next_kind == first:
            selected.emit(2)
        else:
            window.openMediaDetail(next_kind, 2)
        assert stack.property("depth") == 3
        window.openMediaDetail(next_kind, 3)
        assert stack.property("depth") == 4
        stack.property("currentItem").backRequested.emit()
        assert stack.property("depth") == 3
        assert stack.property("currentItem").property("mediaId") == 2
        assert calls[-1] == (next_kind, 2)
        QTest.keyClick(window, Qt.Key.Key_Escape)
        app.processEvents()
        assert stack.property("depth") == 2
        assert stack.property("currentItem").property("mediaId") == 1
        assert calls[-1] == (first, 1)
        window.goBack()
        assert stack.property("depth") == 1
        window.openMediaDetail(first, 9)
        window.navigate(3)
        assert stack.property("depth") == 1
    finally:
        window.close()
        for controller in engine.children():
            if callable(getattr(controller, "close", None)):
                controller.close()
        app.processEvents()


def test_custom_list_status_is_local_and_keeps_order(local_factory):
    service = CustomListsService(local_factory)
    list_id = service.create("Status")
    with local_factory.begin() as session:
        for item_id, status in enumerate([None, *TrackingStatus], start=1):
            movie = MediaRepository(session).upsert(
                item_id, MediaType.MOVIE, str(item_id)
            )
            if status:
                UserMediaRepository(session).set_status(movie.id, status)
    for item_id in range(1, 5):
        service.add(list_id, "movie", item_id)
    items = service.snapshot(list_id)["items"]
    assert [item["tmdb_id"] for item in items] == [1, 2, 3, 4]
    assert [item["status_label"] for item in items] == [
        "İzlenmedi", "İzlenecek", "İzleniyor", "İzlendi"
    ]
    assert [item["watched"] for item in items] == [False, False, False, True]
    with local_factory.begin() as session:
        media = MediaRepository(session).get_by_tmdb(1, MediaType.MOVIE)
        UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHED)
    assert service.snapshot(list_id)["items"][0]["status_label"] == "İzlendi"


@pytest.mark.parametrize("kind", ["movie", "tv"])
def test_back_reloads_real_detail_and_filters_newly_watched_recommendation(
    local_factory, kind,
):
    from copy import deepcopy

    is_movie = kind == "movie"
    first = 42 if is_movie else 77
    second = first + 1
    data = responses() if is_movie else payloads()
    for path, value in list(data.items()):
        other = deepcopy(value)
        if "id" in other:
            other["id"] = second if "/season/" not in path else other["id"] + 100
        data[path.replace(f"/{first}", f"/{second}")] = other
    data[f"/3/{kind}/{first}/recommendations"]["results"] = [
        {"id": second, "title": "Recommended", "original_title": "Recommended",
         "name": "Recommended", "original_name": "Recommended"}
    ]
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=data[request.url.path])
    )) as http:
        service_type = MovieDetailService if is_movie else TvDetailService
        service = service_type(TmdbClient(http, token="test-only"), local_factory)
        service.load(first)
        service.load(second)
        controller_type = MovieDetailController if is_movie else TvDetailController
        controller = controller_type(service, images=DetailImages())
        kwargs = {"movie_controller" if is_movie else "tv_controller": controller}
        app, engine, window = create_application(
            token_controller=TokenController(store=ExistingTokenStore()), **kwargs
        )
        stack = window.findChild(QQuickItem, "contentStack")
        try:
            window.openMediaDetail(kind, first)
            wait_for(app, lambda: controller.detail.get("id") == first)
            page = stack.property("currentItem")
            signal = page.movieSelected if is_movie else page.tvSelected
            signal.emit(second)
            wait_for(app, lambda: controller.detail.get("id") == second)
            if not is_movie:
                wait_for(app, lambda: not controller.seasonBusy)
            controller.setStatus("WATCHED")
            wait_for(app, lambda: not controller.saving)
            stack.property("currentItem").backRequested.emit()
            wait_for(app, lambda: controller.detail.get("id") == first)
            assert stack.property("depth") == 2
            assert stack.property("currentItem").property("mediaId") == first
            assert controller.detail["recommendations"] == []
        finally:
            window.close()
            for child in engine.children():
                if callable(getattr(child, "close", None)):
                    child.close()
            app.processEvents()
