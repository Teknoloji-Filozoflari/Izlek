"""Global search controller and keyboard flow with fake TMDb responses."""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest
from PySide6.QtCore import (
    QObject,
    QPoint,
    QPointF,
    Qt,
    QtMsgType,
    qInstallMessageHandler,
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.security.token_store import StoredToken
from izlek.tmdb.client import NetworkError
from izlek.tmdb.models import MovieDetail, MovieSearchResults, TvSearchResults
from izlek.ui.controllers.movie_detail_controller import MovieDetailController
from izlek.ui.controllers.search_controller import SearchController
from izlek.ui.controllers.token_controller import TokenController


class ExistingTokenStore:
    def load(self):
        return StoredToken("test-only", "keyring")


class FakeImages:
    def poster(self, path, size="grid"):
        result = Future()
        result.set_result(
            Path(__file__).resolve().parents[1]
            / "src/izlek/resources/images/poster-placeholder.svg"
        )
        return result

    def backdrop(self, path):
        return self.poster(path)


class FakeMovieService:
    def __init__(self):
        self.client = FakeTmdb()
        self.status = ""
        self.favorite = False
        self.lists = []

    def load(self, movie_id):
        return {
            "id": movie_id,
            "title": "Original Detail",
            "year": "2022",
            "runtime": 100,
            "genres": ["Drama"],
            "score": 7.2,
            "overview": "Description",
            "posterPath": "",
            "backdropPath": "",
            "cast": [],
            "directors": [],
            "companies": [],
            "countries": [],
            "providers": {},
            "trailerUrl": "",
            "similar": [],
            "recommendations": [],
            "status": self.status,
            "favorite": self.favorite,
            "availableLists": [],
            "lists": self.lists,
        }

    def cached(self, movie_id):
        return None

    def needs_refresh(self, movie_id):
        return True

    def set_status(self, movie_id, status):
        self.status = status
        return self.load(movie_id)

    def set_favorite(self, movie_id, favorite):
        self.favorite = favorite
        return self.load(movie_id)

    def add_to_list(self, movie_id, name):
        self.lists = [name]
        return self.load(movie_id)

    def close(self):
        pass


class FakeTmdb:
    def __init__(self):
        self.block_old = None
        self.calls = []
        self.offline = False

    def search_movie(self, query):
        self.calls.append(("movie", query))
        if self.offline:
            raise NetworkError("offline")
        if query == "old" and self.block_old:
            self.block_old.wait(timeout=2)
        return MovieSearchResults.model_validate(
            {
                "page": 1,
                "total_pages": 1,
                "total_results": 1,
                "results": [
                    {
                        "id": 1,
                        "title": "Türkçe Başlık",
                        "original_title": query + " Original",
                        "release_date": "2022-09-12",
                        "poster_path": "/poster.jpg",
                    }
                ],
            }
        )

    def search_tv(self, query):
        self.calls.append(("tv", query))
        if self.offline:
            raise NetworkError("offline")
        if query == "old" and self.block_old:
            self.block_old.wait(timeout=2)
        return TvSearchResults.model_validate(
            {
                "page": 1,
                "total_pages": 1,
                "total_results": 1,
                "results": [
                    {
                        "id": 2,
                        "name": "Türkçe Dizi",
                        "original_name": query + " Series",
                        "first_air_date": "2021-01-01",
                    }
                ],
            }
        )

    def movie(self, item_id):
        return MovieDetail.model_validate(
            {
                "id": item_id,
                "title": "Türkçe Başlık",
                "original_title": "Original Detail",
                "release_date": "2022-09-12",
                "overview": "Description",
            }
        )


def wait_for(application, condition):
    for _ in range(100):
        application.processEvents()
        if condition():
            return
        QTest.qWait(10)
    raise AssertionError("Timed out waiting for UI state")


def find_visual(item, name):
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = find_visual(child, name)
        if found is not None:
            return found
    return None


@pytest.fixture
def qapp(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    return QGuiApplication.instance() or QGuiApplication([])


def test_controller_separates_media_and_ignores_stale_results(qapp):
    tmdb = FakeTmdb()
    tmdb.block_old = Event()
    with ThreadPoolExecutor(max_workers=4) as executor:
        controller = SearchController(
            client=tmdb, images=FakeImages(), executor=executor
        )
        try:
            controller.search("ab")
            assert tmdb.calls == []
            controller.search("old")
            wait_for(qapp, lambda: len(tmdb.calls) == 2)
            controller.search("new")
            wait_for(qapp, lambda: not controller.busy)
            assert controller.movies[0]["title"] == "new Original"
            assert controller.shows[0]["title"] == "new Series"
            tmdb.block_old.set()
            wait_for(qapp, lambda: len(tmdb.calls) == 4)
            QTest.qWait(20)
            qapp.processEvents()
            assert controller.movies[0]["title"] == "new Original"
            assert controller.shows[0]["title"] == "new Series"
            assert controller.movies[0]["mediaType"] == "movie"
            assert controller.movies[0]["year"] == "2022"
            assert controller.movies[0]["poster"].startswith("file:")
            controller.loadDetail("movie", 1)
            wait_for(qapp, lambda: not controller.detailBusy)
            assert controller.detail["title"] == "Original Detail"
        finally:
            tmdb.block_old.set()
            controller.close()


def test_controller_explains_offline_failure(qapp):
    tmdb = FakeTmdb()
    tmdb.offline = True
    controller = SearchController(client=tmdb, images=FakeImages())
    try:
        controller.search("offline")
        wait_for(qapp, lambda: not controller.busy)
        assert "İnternet bağlantınızı kontrol edin" in controller.error
        assert controller.movies == []
        assert controller.shows == []
        tmdb.offline = False
        controller.search("recovered")
        wait_for(qapp, lambda: not controller.busy)
        assert controller.error == ""
        assert controller.movies[0]["title"] == "recovered Original"
        assert controller.shows[0]["title"] == "recovered Series"
    finally:
        controller.close()


def test_ctrl_k_works_across_pages_escape_and_result_opens_detail(
    qapp, monkeypatch, tmp_path
):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    token = TokenController(store=ExistingTokenStore())
    tmdb = FakeTmdb()
    search = SearchController(client=tmdb, images=FakeImages())
    movie = MovieDetailController(service=FakeMovieService(), images=FakeImages())
    warnings = []

    def collect_warning(kind, context, message):
        if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous_handler = qInstallMessageHandler(collect_warning)
    application, engine, window = create_application(
        token_controller=token, search_controller=search, movie_controller=movie
    )
    try:
        overlay = window.findChild(QObject, "globalSearch")
        stack = window.findChild(QQuickItem, "contentStack")
        for index, name in ((0, "navHome"), (1, "navMovies"), (5, "navSettings")):
            if index:
                item = window.findChild(QQuickItem, name)
                center = item.mapToScene(
                    QPointF(item.width() / 2, item.height() / 2)
                )
                QTest.mouseClick(
                    window,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                    QPoint(int(center.x()), int(center.y())),
                )
                application.processEvents()
            QTest.keyClick(window, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
            wait_for(application, lambda: overlay.property("opened"))
            QTest.keyClick(window, Qt.Key.Key_Escape)
            wait_for(application, lambda: not overlay.property("opened"))

        QTest.keyClick(window, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
        wait_for(application, lambda: overlay.property("opened"))
        field = window.findChild(QQuickItem, "globalSearchInput")
        field.setProperty("text", "a")
        field.setProperty("text", "ar")
        assert tmdb.calls == []
        field.setProperty("text", "arr")
        field.setProperty("text", "arri")
        field.setProperty("text", "arrival")
        wait_for(application, lambda: len(search.movies) > 0 and not search.busy)
        assert tmdb.calls == [("movie", "arrival"), ("tv", "arrival")] or (
            tmdb.calls == [("tv", "arrival"), ("movie", "arrival")]
        )
        wait_for(
            application,
            lambda: find_visual(
                overlay.property("contentItem"), "movieSearchResult"
            ) is not None,
        )
        card = find_visual(overlay.property("contentItem"), "movieSearchResult")
        center = card.mapToScene(QPointF(card.width() / 2, card.height() / 2))
        QTest.mouseClick(
            window,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(int(center.x()), int(center.y())),
        )
        wait_for(
            application,
            lambda: stack.property("currentItem").property("pageTitle")
            == "Film Detayı",
        )
        wait_for(application, lambda: movie.detail.get("title") == "Original Detail")
        assert not overlay.property("opened")
        assert field is not None
        QTest.qWait(200)
        application.processEvents()
        add_button = window.findChild(QQuickItem, "addMovieToLibrary")
        add_button.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        wait_for(application, lambda: movie.detail.get("status") == "PLANNED")
        favorite = window.findChild(QQuickItem, "movieFavorite")
        favorite.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        wait_for(application, lambda: movie.detail.get("favorite") is True)
        list_open = window.findChild(QQuickItem, "movieListOpen")
        list_open.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        list_dialog = window.findChild(QObject, "movieListDialog")
        wait_for(application, lambda: list_dialog.property("opened"))
        list_name = window.findChild(QQuickItem, "movieListName")
        list_name.setProperty("text", "Hafta Sonu")
        list_add = window.findChild(QQuickItem, "movieListAdd")
        list_add.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        wait_for(application, lambda: movie.detail.get("lists") == ["Hafta Sonu"])
        assert not warnings
    finally:
        window.close()
        search.close()
        movie.close()
        application.processEvents()
        qInstallMessageHandler(previous_handler)
