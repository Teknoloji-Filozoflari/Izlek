"""Reproduce audit findings using isolated databases and controlled workers."""

import json
from threading import Event, Thread

import httpx
import pytest
from PySide6.QtGui import QGuiApplication

from izlek.cache.images import ImageDiskCache
from izlek.core.paths import app_paths
from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.services.movie_detail import MovieDetailService
from izlek.services.transfer import TransferService
from izlek.services.tv_detail import TvDetailService
from izlek.tmdb.client import TmdbClient
from izlek.ui.controllers.cache_controller import CacheController
from izlek.ui.controllers.movie_detail_controller import MovieDetailController
from izlek.ui.controllers.tv_detail_controller import TvDetailController
from test_movie_detail import FakeImages as MovieImages
from test_movie_detail import responses
from test_tv_detail import FakeImages as TvImages
from test_tv_detail import payloads


@pytest.fixture(params=["movie", "tv"])
def detail_case(request, tmp_path):
    kind = request.param
    data = responses() if kind == "movie" else payloads()
    item_id = 42 if kind == "movie" else 77
    engine = initialize_database(tmp_path / "detail.sqlite3")
    with httpx.Client(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json=data[req.url.path])
    )) as http:
        client = TmdbClient(http, token="test-only")
        service_type = MovieDetailService if kind == "movie" else TvDetailService
        service = service_type(client, create_session_factory(engine))
        service.load(item_id)
        app = QGuiApplication.instance() or QGuiApplication([])
        controller_type = (
            MovieDetailController if kind == "movie" else TvDetailController
        )
        controller = controller_type(
            service, images=MovieImages() if kind == "movie" else TvImages()
        )
        controller._detail = service.cached(item_id)
        try:
            yield app, controller, service, item_id
        finally:
            controller.close()
            app.processEvents()
            engine.dispose()


def test_queued_detail_write_survives_page_navigation(detail_case):
    app, controller, service, item_id = detail_case
    executor = getattr(controller, "_write_executor", controller._executor)
    release = Event()
    entered = [Event() for _ in range(executor._max_workers)]

    def block(started):
        started.set()
        assert release.wait(timeout=5)

    blockers = [executor.submit(block, event) for event in entered]
    try:
        assert all(event.wait(timeout=2) for event in entered)
        controller.setStatus("WATCHED")
        controller.cancelPending()
    finally:
        release.set()
        for future in blockers:
            future.result(timeout=2)
        executor.shutdown(wait=True)
    app.processEvents()
    assert service.cached(item_id)["status"] == "WATCHED"


def test_completed_write_notifies_library_after_leaving_detail(
    detail_case, monkeypatch,
):
    app, controller, service, item_id = detail_case
    entered, release = Event(), Event()
    original = service.set_status

    def delayed_save(*args):
        entered.set()
        assert release.wait(timeout=5)
        return original(*args)

    monkeypatch.setattr(service, "set_status", delayed_save)
    notifications = []
    controller.libraryChanged.connect(lambda: notifications.append(True))
    try:
        controller.setStatus("WATCHED")
        assert entered.wait(timeout=2)
        controller.cancelPending()
        controller._detail = {"id": 999, "title": "New page"}
    finally:
        release.set()
        getattr(controller, "_write_executor", controller._executor).shutdown(wait=True)
    app.processEvents()
    assert service.cached(item_id)["status"] == "WATCHED"
    assert controller.detail == {"id": 999, "title": "New page"}
    assert notifications == [True]


def test_shutdown_drains_accepted_detail_writes(detail_case):
    _, controller, service, item_id = detail_case
    release, entered = Event(), Event()

    def block():
        entered.set()
        assert release.wait(timeout=5)

    blocker = controller._write_executor.submit(block)
    assert entered.wait(timeout=2)
    controller.setStatus("WATCHED")
    closer = Thread(target=controller.close)
    closer.start()
    try:
        release.set()
        blocker.result(timeout=2)
        closer.join(timeout=3)
        assert not closer.is_alive()
        assert service.cached(item_id)["status"] == "WATCHED"
    finally:
        release.set()
        closer.join(timeout=3)


def test_imported_cast_is_normalized_before_detail_presentation(detail_case, tmp_path):
    _, _, service, item_id = detail_case
    transfer = TransferService(service._sessions())
    document = transfer.build_export().model_dump(mode="json")
    cast = document["media"][0]["metadata"]["credits"]["cast"]
    cast[0]["order"] = "1"
    cast.append({"id": 90, "name": "First actor", "order": 0})
    path = tmp_path / "cast.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    transfer.import_file(path)
    assert service.cached(item_id)["cast"][0]["name"] == "First actor"


def test_previously_imported_cast_is_read_with_validated_types(detail_case):
    _, _, service, item_id = detail_case
    kind = MediaType.MOVIE if item_id == 42 else MediaType.TV
    with service._sessions().begin() as session:
        media = MediaRepository(session).get_by_tmdb(item_id, kind)
        blob = json.loads(json.dumps(media.metadata_json))
        cast = blob["credits"]["cast"]
        cast[0]["order"] = "1"
        cast.append({"id": 90, "name": "First actor", "order": 0})
        # Assign a new object so SQLAlchemy persists nested JSON changes.
        media.metadata_json = blob
    assert service.cached(item_id)["cast"][0]["name"] == "First actor"


def test_cache_maintenance_finishes_with_unreadable_token(tmp_path):
    app = QGuiApplication.instance() or QGuiApplication([])
    engine = initialize_database()
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(
            42, MediaType.MOVIE, "Local film", poster_path="/cached.jpg"
        )
        UserMediaRepository(session).set_status(media.id, TrackingStatus.PLANNED)
    cache = ImageDiskCache()
    cached = cache.put("poster-detail", "/cached.jpg", b"cached-image")
    token = app_paths().config / "tmdb-token"
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_bytes(b"\xff\xfe\xff")
    token.chmod(0o600)
    controller = CacheController(cache=cache)
    try:
        controller._executor.submit(lambda: None).result(timeout=5)
        app.processEvents()
        assert not controller.busy
        assert controller.feedback == ""
        assert controller.sizeBytes == len(b"cached-image")
        assert cached.is_file()
    finally:
        controller.close()
        engine.dispose()
