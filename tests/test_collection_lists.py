"""TMDb collection/franchise → local custom list import."""


import httpx
from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem

from izlek.app import create_application
from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.services.custom_lists import CustomListsService
from izlek.services.movie_detail import MovieDetailService
from izlek.tmdb.client import TmdbClient
from izlek.ui.controllers.custom_lists_controller import CustomListsController
from izlek.ui.controllers.movie_detail_controller import MovieDetailController
from izlek.ui.controllers.token_controller import TokenController
from test_movie_detail import FakeImages, responses, wait_for
from test_tv_detail import ExistingTokenStore


def _collection_payload():
    movie = responses()["/3/movie/42"]
    movie = {
        **movie,
        "belongs_to_collection": {
            "id": 10,
            "name": "Example Collection",
            "poster_path": "/c.jpg",
            "backdrop_path": "/cb.jpg",
        },
    }
    payload = responses()
    payload["/3/movie/42"] = movie
    payload["/3/collection/10"] = {
        "id": 10,
        "name": "Example Collection",
        "overview": "A franchise.",
        "parts": [
            {
                "id": 42,
                "title": "One",
                "original_title": "Original Film",
                "overview": "A film.",
                "poster_path": "/poster.jpg",
                "release_date": "2024-02-03",
                "vote_average": 7.6,
            },
            {
                "id": 43,
                "title": "Two",
                "original_title": "Sequel Film",
                "overview": "Another film.",
                "poster_path": "/sequel.jpg",
                "release_date": "2025-03-04",
                "vote_average": 7.1,
            },
            {
                "id": 44,
                "title": "Three",
                "original_title": "Third Film",
                "overview": "",
                "poster_path": None,
                "release_date": "2026-01-01",
                "vote_average": 0,
            },
        ],
    }
    return payload


def test_add_collection_movies_creates_list_without_forcing_library(tmp_path):
    engine = initialize_database(tmp_path / "collection.sqlite3")
    factory = create_session_factory(engine)
    service = CustomListsService(factory)
    summary = service.add_collection_movies(
        "Example Collection",
        [
            {"tmdb_id": 42, "title": "Original Film", "release_date": "2024-02-03"},
            {"tmdb_id": 43, "title": "Sequel Film", "poster_path": "/s.jpg"},
        ],
    )
    assert summary["created"] is True
    assert summary["added"] == 2
    assert summary["total"] == 2
    items = service.snapshot(summary["listId"])["items"]
    assert [(item["kind"], item["title"], item["status"]) for item in items] == [
        ("movie", "Original Film", ""),
        ("movie", "Sequel Film", ""),
    ]
    with factory() as session:
        media = MediaRepository(session).get_by_tmdb(43, MediaType.MOVIE)
        assert media is not None
        assert UserMediaRepository(session).get(media.id) is None
    again = service.add_collection_movies(
        "example collection",
        [
            {"tmdb_id": 42, "title": "Original Film"},
            {"tmdb_id": 43, "title": "Sequel Film"},
            {"tmdb_id": 44, "title": "Third Film"},
        ],
    )
    assert again["created"] is False
    assert again["listId"] == summary["listId"]
    assert again["added"] == 1
    assert again["already"] == 2
    assert [
        item["title"] for item in service.snapshot(summary["listId"])["items"]
    ] == ["Original Film", "Sequel Film", "Third Film"]
    service.remove(summary["listId"], "movie", 43)
    assert [
        item["title"] for item in service.snapshot(summary["listId"])["items"]
    ] == ["Original Film", "Third Film"]
    service.close()
    engine.dispose()


def test_movie_detail_imports_tmdb_collection_into_list(tmp_path):
    if QGuiApplication.instance() is None:
        QGuiApplication([])
    db = initialize_database(tmp_path / "movie-collection.sqlite3")
    factory = create_session_factory(db)
    payload = _collection_payload()
    warnings = []

    def collect(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous = qInstallMessageHandler(collect)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload[request.url.path])
        )
    ) as http:
        movie = MovieDetailController(
            MovieDetailService(
                TmdbClient(http, token="test-only"), factory
            ),
            images=FakeImages(),
        )
        lists = CustomListsController(service=CustomListsService(factory))
        application, _engine, window = create_application(
            token_controller=TokenController(store=ExistingTokenStore()),
            movie_controller=movie,
            custom_lists_controller=lists,
        )
        try:
            window.openMediaDetail("movie", 42)
            wait_for(
                application,
                lambda: not movie.busy and movie.detail.get("collectionId") == 10,
            )
            button = window.findChild(QQuickItem, "movieCollectionToList")
            assert button is not None and button.isVisible()
            movie.addCollectionToList()
            wait_for(application, lambda: not movie.saving and movie.feedback)
            assert "Example Collection" in movie.feedback
            assert "3/3" in movie.feedback or "3" in movie.feedback
            lists.refresh()
            wait_for(application, lambda: not lists.busy)
            custom = [item for item in lists.lists if not item.get("smart")]
            assert len(custom) == 1
            assert custom[0]["name"] == "Example Collection"
            assert custom[0]["count"] == 3
            with factory() as session:
                sequel = MediaRepository(session).get_by_tmdb(43, MediaType.MOVIE)
                assert sequel is not None
                user = UserMediaRepository(session).get(sequel.id)
                assert user is None or user.status is None
                current = MediaRepository(session).get_by_tmdb(42, MediaType.MOVIE)
                assert current is not None
            # Second import is idempotent for membership.
            movie.addCollectionToList()
            wait_for(application, lambda: not movie.saving)
            lists.refresh()
            wait_for(application, lambda: not lists.busy)
            custom = [item for item in lists.lists if not item.get("smart")]
            assert custom[0]["count"] == 3
            assert not warnings
        finally:
            window.close()
            movie.close()
            lists.close()
            application.processEvents()
            qInstallMessageHandler(previous)
    db.dispose()
