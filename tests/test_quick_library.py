"""One-click additions preserve watched state and cached detailed metadata."""

from datetime import date

import pytest

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.services.quick_library import QuickLibraryService


def test_quick_add_movie_tv_and_restart_preserve_state(tmp_path):
    engine = initialize_database(tmp_path / "quick.sqlite3")
    factory = create_session_factory(engine)
    service = QuickLibraryService(factory)
    try:
        for kind in ("movie", "tv"):
            summary = {"mediaType": kind, "id": 42, "title": "Original",
                       "releaseDate": "2024-03-01", "posterPath": f"/{kind}.jpg"}
            service.add(summary)
            service.add(summary)
        assert service.states() == {"movie:42": "added", "tv:42": "added"}
        with factory.begin() as session:
            repo = MediaRepository(session)
            movie = repo.get_by_tmdb(42, MediaType.MOVIE)
            tv = repo.get_by_tmdb(42, MediaType.TV)
            users = UserMediaRepository(session)
            assert users.get(movie.id).status == TrackingStatus.PLANNED
            assert users.get(tv.id).status == TrackingStatus.WATCHING
            assert movie.release_date == tv.first_air_date == date(2024, 3, 1)
            assert movie.poster_path == "/movie.jpg" and tv.poster_path == "/tv.jpg"
            assert movie.last_synced_at is None and tv.last_synced_at is None
            users.set_status(tv.id, TrackingStatus.WATCHED)
            users.set_favorite(tv.id, True)
            tv.overview = "Full detail"
        service.add({"mediaType": "tv", "id": 42, "title": "Partial",
                     "posterPath": "/different.jpg"})
        with factory() as session:
            tv = MediaRepository(session).get_by_tmdb(42, MediaType.TV)
            user = UserMediaRepository(session).get(tv.id)
            assert user.status == TrackingStatus.WATCHED and user.favorite
            assert tv.original_title == "Original" and tv.overview == "Full detail"
            assert tv.poster_path == "/tv.jpg"
        reopened = QuickLibraryService(factory)
        assert reopened.states() == service.states()
        for summary in ({"mediaType": "person", "id": 2, "title": "Invalid"},
                        {"mediaType": "movie", "id": -1, "title": "Invalid"}):
            with pytest.raises(ValueError):
                service.add(summary)
    finally:
        service.close()
        engine.dispose()


def test_quick_add_controller_reports_failure_and_can_retry():
    from PySide6.QtGui import QGuiApplication

    from izlek.ui.controllers.quick_library_controller import QuickLibraryController
    from test_global_search import wait_for

    class Service:
        fail = True
        calls = 0

        def add(self, summary):
            self.calls += 1
            if self.fail:
                raise OSError("Database unavailable")

        def states(self):
            return {} if self.fail else {"tv:1": "added"}

        def close(self):
            pass

    application = QGuiApplication.instance() or QGuiApplication([])
    service = Service()
    controller = QuickLibraryController(service)
    try:
        item = {"mediaType": "tv", "id": 1, "title": "Show"}
        controller.add(item)
        controller.add(item)
        assert controller.states == {"tv:1": "adding"}
        wait_for(application, lambda: bool(controller.error))
        assert controller.states == {} and service.calls == 1
        service.fail = False
        controller.add(item)
        wait_for(application, lambda: controller.states == {"tv:1": "added"})
        assert controller.error == ""
        controller.add(item)
        assert service.calls == 2
    finally:
        controller.close()
