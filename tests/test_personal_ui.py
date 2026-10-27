"""Real QML review editing, selected batches and reversible discovery dismissal."""

import httpx
import pytest
from PySide6.QtCore import QObject, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.services.custom_lists import CustomListsService
from izlek.services.movie_detail import MovieDetailService
from izlek.services.movie_library import MovieLibraryService
from izlek.services.personal_media import PersonalMediaService
from izlek.services.tv_detail import TvDetailService
from izlek.services.tv_library import TvLibraryService
from izlek.tmdb.client import TmdbClient
from izlek.ui.controllers.discover_controller import DiscoverController
from izlek.ui.controllers.movie_detail_controller import MovieDetailController
from izlek.ui.controllers.movie_library_controller import MovieLibraryController
from izlek.ui.controllers.personal_media_controller import PersonalMediaController
from izlek.ui.controllers.token_controller import TokenController
from izlek.ui.controllers.tv_detail_controller import TvDetailController
from izlek.ui.controllers.tv_library_controller import TvLibraryController
from test_discover import _DiscoverClient
from test_global_search import ExistingTokenStore, FakeImages, find_visual, wait_for
from test_movie_detail import responses
from test_tv_detail import FakeImages as DetailImages
from test_tv_detail import payloads

pytest_plugins = ("test_personal_features",)


def close_all(app, engine, window):
    window.close()
    for child in engine.children():
        if callable(getattr(child, "close", None)):
            child.close()
    app.processEvents()


@pytest.mark.parametrize("kind", ["movie", "tv"])
def test_review_edit_save_clear_and_dismiss_restore_in_qml(personal_factory, kind):
    data = responses() if kind == "movie" else payloads()
    item_id = 42 if kind == "movie" else 77
    service = PersonalMediaService(personal_factory)
    personal = PersonalMediaController(service)
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
        details_service = service_type(
            TmdbClient(http, token="test-only"), personal_factory
        )
        details_service.load(item_id)
        details_type = MovieDetailController if kind == "movie" else TvDetailController
        details = details_type(details_service, images=DetailImages())
        app, engine, window = create_application(
            token_controller=TokenController(store=ExistingTokenStore()),
            personal_media_controller=personal,
            **{kind + "_controller": details},
        )
        try:
            window.openMediaDetail(kind, item_id)
            wait_for(
                app,
                lambda: (
                    personal.current.get("id") == item_id
                    and not personal.busy
                    and not details.busy
                    and bool(details.detail.get("title"))
                ),
            )
            rating = window.findChild(QQuickItem, "personalRatingInput")
            note = window.findChild(QQuickItem, "personalNoteInput")
            review = window.findChild(QQuickItem, kind + "PersonalReview")
            toggle = window.findChild(QQuickItem, "togglePersonalReviewButton")
            assert toggle.isVisible() and not review.property("expanded")
            assert not rating.isVisible() and not note.isVisible()
            toggle.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Space)
            wait_for(app, lambda: note.isVisible() and review.isVisible())
            rating.setProperty("currentIndex", 8)
            rating.activated.emit(8)
            note.setProperty("text", "Güzel final.\nTekrar izlenir 🎬")
            # Collapsing the form preserves an unsaved draft without writing it.
            toggle.clicked.emit()
            app.processEvents()
            assert not note.isVisible() and not review.property("expanded")
            assert service.read(kind, item_id)["note"] == ""
            toggle.clicked.emit()
            app.processEvents()
            assert note.isVisible()
            assert note.property("text") == "Güzel final.\nTekrar izlenir 🎬"
            assert rating.property("currentIndex") == 8
            save = window.findChild(QQuickItem, "savePersonalReviewButton")
            save.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Space)
            wait_for(
                app, lambda: not personal.busy and personal.current.get("rating") == 8
            )
            assert (
                service.read(kind, item_id)["note"] == "Güzel final.\nTekrar izlenir 🎬"
            )
            # Reopen the same detail and prove the draft is filled from SQLite.
            window.goBack()
            window.openMediaDetail(kind, item_id)
            wait_for(
                app, lambda: personal.current.get("id") == item_id and not personal.busy
            )
            page = window.findChild(QQuickItem, "contentStack").property("currentItem")
            note = page.findChild(QQuickItem, "personalNoteInput")
            assert not note.isVisible()
            page.findChild(QQuickItem, "togglePersonalReviewButton").clicked.emit()
            wait_for(app, lambda: note.isVisible())
            wait_for(
                app,
                lambda: note.property("text") == "Güzel final.\nTekrar izlenir 🎬",
            )
            rating = page.findChild(QQuickItem, "personalRatingInput")
            assert rating.property("currentIndex") == 8
            rating.setProperty("currentIndex", 0)
            note.setProperty("text", "")
            page.findChild(QQuickItem, "savePersonalReviewButton").clicked.emit()
            wait_for(
                app, lambda: not personal.busy and personal.current.get("rating") == 0
            )
            page.findChild(QQuickItem, "dismissMediaButton").clicked.emit()
            wait_for(
                app, lambda: not personal.busy and personal.current.get("dismissed")
            )
            window.navigate(5)
            wait_for(app, lambda: len(personal.hiddenItems) == 1)
            view = window.findChild(QQuickItem, "hiddenMediaList")
            restore = find_visual(view, "restoreHiddenMediaButton")
            assert restore is not None
            restore.clicked.emit()
            wait_for(app, lambda: not personal.busy and not personal.hiddenItems)
            assert service.suppressed_ids(kind) == set()
            assert not warnings
        finally:
            close_all(app, engine, window)
            qInstallMessageHandler(previous)


@pytest.mark.parametrize("kind", ["movie", "tv"])
def test_library_filter_selection_confirm_batch_favorite_and_list(
    personal_factory, kind
):
    list_service = CustomListsService(personal_factory)
    list_id = list_service.create("UI batch")
    controller_type = MovieLibraryController if kind == "movie" else TvLibraryController
    service_type = MovieLibraryService if kind == "movie" else TvLibraryService
    library = controller_type(service_type(personal_factory), images=FakeImages())
    warnings = []

    def collect(level, context, message):
        if level in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            warnings.append(message)

    previous = qInstallMessageHandler(collect)
    app, engine, window = create_application(
        token_controller=TokenController(store=ExistingTokenStore()),
        **{kind + "_library_controller": library},
    )
    try:
        window.resize(1366, 768)
        window.navigate(1 if kind == "movie" else 2)
        wait_for(app, lambda: not library.busy and len(library.items) == 5)
        window.findChild(QQuickItem, "toggleLibraryFiltersButton").clicked.emit()
        state = window.findChild(QQuickItem, "libraryStatusFilter")
        state.setProperty("currentIndex", 1)
        genre = window.findChild(QQuickItem, "libraryGenreFilter")
        genre.setProperty("currentIndex", 1)
        genre.activated.emit(1)
        window.findChild(QQuickItem, "libraryYearFromFilter").setProperty(
            "text", "2020"
        )
        window.findChild(QQuickItem, "libraryYearToFilter").setProperty("text", "2023")
        window.findChild(QQuickItem, "libraryRuntimeFilter").setProperty(
            "text", "100" if kind == "movie" else "45"
        )
        window.findChild(QQuickItem, "libraryScoreFilter").setProperty("value", 75)
        window.findChild(QQuickItem, "applyLibraryFiltersButton").clicked.emit()
        wait_for(app, lambda: not library.busy and len(library.items) == 1)
        assert library.items[0]["tmdb_id"] == 1 and library.filtersActive
        window.findChild(QQuickItem, "toggleLibrarySelectionButton").clicked.emit()
        grid = window.findChild(QQuickItem, kind + "LibraryGrid")
        grid.property("currentItem").activated.emit()
        assert window.findChild(QQuickItem, "contentStack").property("depth") == 1
        window.findChild(QQuickItem, "openLibraryBatchButton").clicked.emit()
        dialog = window.findChild(QObject, "libraryBulkDialog")
        wait_for(app, lambda: dialog.property("opened"))
        apply = window.findChild(QQuickItem, "applyLibraryBatchButton")
        apply.clicked.emit()
        confirm = window.findChild(QObject, "libraryBatchConfirm")
        wait_for(app, lambda: confirm.property("opened"))
        assert library.items[0]["status"] == "PLANNED"
        confirm.reject()
        assert library.items[0]["status"] == "PLANNED"
        apply.clicked.emit()
        wait_for(app, lambda: confirm.property("opened"))
        confirm.accept()
        wait_for(
            app,
            lambda: (
                not library.busy and not library.batchBusy and len(library.items) == 0
            ),
        )
        with personal_factory() as session:
            media = MediaRepository(session).get_by_tmdb(1, MediaType(kind.upper()))
            assert (
                UserMediaRepository(session).get(media.id).status
                == TrackingStatus.WATCHED
            )
        window.findChild(QQuickItem, "clearLibraryFiltersButton").clicked.emit()
        wait_for(app, lambda: not library.busy and len(library.items) == 5)
        for action in (3, 5):
            window.findChild(QQuickItem, "toggleLibrarySelectionButton").clicked.emit()
            window.findChild(QQuickItem, "selectVisibleLibraryButton").clicked.emit()
            window.findChild(QQuickItem, "openLibraryBatchButton").clicked.emit()
            wait_for(app, lambda: dialog.property("opened"))
            window.findChild(QQuickItem, "libraryBatchAction").setProperty(
                "currentIndex", action
            )
            apply.clicked.emit()
            wait_for(
                app,
                lambda: (
                    not library.busy
                    and not library.batchBusy
                    and not dialog.property("visible")
                ),
            )
        assert len(library.favorites) == 5
        assert len(list_service.snapshot(list_id)["items"]) == 5
        for width, height in ((850, 768), (1366, 768), (1920, 1080)):
            window.resize(width, height)
            app.processEvents()
            panel = window.findChild(QQuickItem, "libraryFiltersPanel")
            assert panel.width() > 400 and panel.height() > 0
        assert not warnings
    finally:
        close_all(app, engine, window)
        qInstallMessageHandler(previous)


def test_discovery_hide_button_filters_in_memory_and_settings_restores(
    personal_factory,
):
    prefs = PersonalMediaService(personal_factory)
    personal = PersonalMediaController(PersonalMediaService(personal_factory))
    client = _DiscoverClient()
    discover = DiscoverController(client=client, images=FakeImages(), preferences=prefs)
    app, engine, window = create_application(
        token_controller=TokenController(store=ExistingTokenStore()),
        personal_media_controller=personal,
        discover_controller=discover,
    )
    try:
        wait_for(app, lambda: not discover.busy and bool(discover.items))
        grid = window.findChild(QQuickItem, "discoverResults")
        button = find_visual(
            grid.property("currentItem"), "dismissRecommendationButton"
        )
        assert button is not None and button.isVisible()
        button.clicked.emit()
        wait_for(app, lambda: not personal.busy and discover.items == [])
        assert len(client.calls) == 1
        personal.setDismissed({"id": 10, "mediaType": "movie"}, False)
        wait_for(app, lambda: not personal.busy and bool(discover.items))
        assert len(client.calls) == 1
    finally:
        close_all(app, engine, window)


