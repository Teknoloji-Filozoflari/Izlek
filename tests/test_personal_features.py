"""Personal data, combined offline filters and atomic selection writes."""

import json
from datetime import date
from threading import Event, Thread

import httpx
import pytest
from PySide6.QtGui import QGuiApplication
from sqlalchemy import select

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import EpisodeProgress, MediaType, TrackingStatus
from izlek.repositories.local import (
    EpisodeRepository,
    MediaRepository,
    SeasonRepository,
    UserMediaRepository,
)
from izlek.services.custom_lists import CustomListsService
from izlek.services.library_filters import LibraryFilters
from izlek.services.movie_detail import MovieDetailService
from izlek.services.movie_library import MovieLibraryService
from izlek.services.personal_media import PersonalMediaService
from izlek.services.transfer import TransferService
from izlek.services.tv_detail import TvDetailService
from izlek.services.tv_library import TvLibraryService
from izlek.tmdb.client import TmdbClient
from izlek.ui.controllers.discover_controller import DiscoverController
from izlek.ui.controllers.movie_library_controller import MovieLibraryController
from izlek.ui.controllers.personal_media_controller import PersonalMediaController
from test_discover import _DiscoverClient
from test_global_search import FakeImages, wait_for
from test_movie_detail import responses
from test_tv_detail import payloads


@pytest.fixture
def personal_factory(tmp_path):
    engine = initialize_database(tmp_path / "personal.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        for kind in MediaType:
            for item_id in range(1, 6):
                year = {1: 2021, 2: 2020, 4: 2024, 5: 2021}.get(item_id)
                media = MediaRepository(session).upsert(
                    item_id,
                    kind,
                    f"Item {item_id}",
                    release_date=date(year, 1, 1) if year else None,
                    first_air_date=date(year, 1, 1) if year else None,
                    runtime={1: 90, 2: 150, 4: 80, 5: 85}.get(item_id)
                    if kind == MediaType.MOVIE
                    else None,
                    metadata_json={
                        "detail": {
                            "id": item_id,
                            "title": f"Item {item_id}",
                            "original_title": f"Item {item_id}",
                            "name": f"Item {item_id}",
                            "original_name": f"Item {item_id}",
                            "genres": [
                                {
                                    "id": 1,
                                    "name": "SciFi" if item_id in (3, 4) else "Dram",
                                }
                            ],
                            "episode_run_time": [
                                {1: 40, 2: 60, 4: 30, 5: 50}.get(item_id)
                            ]
                            if item_id != 3
                            else [],
                            **(
                                {
                                    "vote_average": {1: 8.0, 2: 9.0, 4: 7.0, 5: 8.5}[
                                        item_id
                                    ]
                                }
                                if item_id != 3
                                else {}
                            ),
                        }
                    },
                )
                user = UserMediaRepository(session).set_status(
                    media.id,
                    {2: TrackingStatus.WATCHED, 5: TrackingStatus.WATCHING}.get(
                        item_id, TrackingStatus.PLANNED
                    ),
                )
                user.sort_order = item_id - 1
            tv = MediaRepository(session).get_by_tmdb(1, MediaType.TV)
            if kind == MediaType.TV:
                season = SeasonRepository(session).upsert(tv.id, 1)
                first = EpisodeRepository(session).upsert(season.id, 1)
                EpisodeRepository(session).upsert(season.id, 2)
                EpisodeRepository(session).set_watched(first.id, True)
    try:
        yield factory
    finally:
        engine.dispose()


def test_reviews_preserve_tracking_and_survive_metadata_changes(personal_factory):
    service = PersonalMediaService(personal_factory)
    with personal_factory() as session:
        media = MediaRepository(session).get_by_tmdb(1, MediaType.MOVIE)
        old = UserMediaRepository(session).get(media.id)
        before = (old.status, old.status_is_manual, old.sort_order, old.added_at)
    note = "Tekrar izlenir.\nFinal güzeldi — şğüöı 🎬"
    assert service.save_review("movie", 1, 9, note)["rating"] == 9
    with personal_factory.begin() as session:
        MediaRepository(session).upsert(1, MediaType.MOVIE, "Refreshed", runtime=100)
        user = UserMediaRepository(session).get(media.id)
        assert (
            user.status,
            user.status_is_manual,
            user.sort_order,
            user.added_at,
        ) == before
    assert service.read("movie", 1)["note"] == note
    assert service.read("tv", 1)["rating"] == 0
    assert service.read("tv", 1)["note"] == ""
    service.save_review("movie", 1, 0, "")
    assert service.read("movie", 1)["rating"] == 0
    assert service.read("movie", 1)["note"] == ""


@pytest.mark.parametrize("rating", [-1, 11, True, 2.5])
def test_invalid_personal_ratings_do_not_write(personal_factory, rating):
    service = PersonalMediaService(personal_factory)
    with pytest.raises(ValueError):
        service.save_review("movie", 1, rating, "must not save")
    assert service.read("movie", 1)["note"] == ""


def test_note_length_and_unknown_media_are_validated(personal_factory):
    service = PersonalMediaService(personal_factory)
    with pytest.raises(ValueError):
        service.save_review("movie", 1, 7, "x" * 2001)
    with pytest.raises(LookupError):
        service.save_review("movie", 999, 7, "note")
    service.save_review("movie", 1, 7, "x" * 2000)
    assert len(service.read("movie", 1)["note"]) == 2000


def test_dismissal_does_not_add_library_membership_and_can_be_restored(
    personal_factory,
):
    service = PersonalMediaService(personal_factory)
    media = {
        "id": 99,
        "mediaType": "movie",
        "title": "Dismissed",
        "posterPath": "/poster.jpg",
    }
    service.dismiss(media, True)
    assert service.suppressed_ids("movie") == {99}
    assert service.suppressed_ids("tv") == set()
    with personal_factory() as session:
        item = MediaRepository(session).get_by_tmdb(99, MediaType.MOVIE)
        user = UserMediaRepository(session).get(item.id)
        assert user.status is None and not user.favorite
    assert service.hidden()[0]["title"] == "Dismissed"
    service.dismiss(media, False)
    assert service.hidden() == []
    assert len(MovieLibraryService(personal_factory).snapshot(None).items) == 5


@pytest.mark.parametrize("kind", [MediaType.MOVIE, MediaType.TV])
def test_combined_filters_use_cached_values_and_exclude_unknowns(
    personal_factory, kind
):
    service_type = MovieLibraryService if kind == MediaType.MOVIE else TvLibraryService
    service = service_type(personal_factory)
    filters = LibraryFilters.parse(
        {
            "status": "PLANNED",
            "genre": "Dram",
            "year_from": "2020",
            "year_to": "2023",
            "max_runtime": 100 if kind == MediaType.MOVIE else 45,
            "min_score": 7.5,
        }
    )
    result = service.snapshot(None, "custom", filters=filters)
    assert [row.tmdb_id for row in result.items] == [1]
    assert result.genres == ["Dram", "SciFi"]
    assert result.stats["total"] == 5
    assert len(service.snapshot(None).items) == 5
    assert 3 not in [
        row.tmdb_id
        for row in service.snapshot(None, filters=LibraryFilters(year_from=2000)).items
    ]
    assert 3 not in [
        row.tmdb_id
        for row in service.snapshot(None, filters=LibraryFilters(max_runtime=100)).items
    ]


@pytest.mark.parametrize(
    "values",
    [
        {"year_from": 2025, "year_to": 2020},
        {"year_from": 1800},
        {"status": "INVALID"},
        {"max_runtime": -1},
        {"min_score": float("nan")},
    ],
)
def test_invalid_filter_ranges_are_rejected(values):
    with pytest.raises(ValueError):
        LibraryFilters.parse(values)


def test_batch_validates_all_before_writing_and_deduplicates_lists(personal_factory):
    service = PersonalMediaService(personal_factory)
    lists = CustomListsService(personal_factory)
    list_id = lists.create("Batch")
    with pytest.raises(LookupError):
        service.batch("movie", [1, 999], "WATCHED")
    assert (
        MovieLibraryService(personal_factory).snapshot(None, "custom").items[0].status
        == "PLANNED"
    )
    assert service.batch("movie", [1, 2, 1], "favorite") == 2
    assert len(MovieLibraryService(personal_factory).snapshot(None).favorites) == 2
    assert service.batch("movie", [1, 2, 1], "list", list_id) == 2
    service.batch("movie", [1, 2], "list", list_id)
    assert len(lists.snapshot(list_id)["items"]) == 2
    with pytest.raises(LookupError):
        service.batch("movie", [3, 4], "list", 999)
    service.batch("movie", [1, 2], "unfavorite")
    assert MovieLibraryService(personal_factory).snapshot(None).favorites == []


def test_tv_batch_status_preserves_episode_marks_and_personal_data(personal_factory):
    service = PersonalMediaService(personal_factory)
    service.save_review("tv", 1, 8, "keep")
    with personal_factory() as session:
        before = [
            (row.episode_id, row.watched, row.watched_at)
            for row in session.scalars(select(EpisodeProgress))
        ]
    service.batch("tv", [1, 2], "WATCHED")
    with personal_factory() as session:
        assert before == [
            (row.episode_id, row.watched, row.watched_at)
            for row in session.scalars(select(EpisodeProgress))
        ]
        tv = MediaRepository(session).get_by_tmdb(1, MediaType.TV)
        user = UserMediaRepository(session).get(tv.id)
        assert user.status == TrackingStatus.WATCHED and user.status_is_manual
        assert user.personal_rating == 8 and user.personal_note == "keep"
        movie = MediaRepository(session).get_by_tmdb(1, MediaType.MOVIE)
        assert (
            UserMediaRepository(session).get(movie.id).status == TrackingStatus.PLANNED
        )


def test_personal_preferences_export_import_and_explicit_clear(
    personal_factory, tmp_path
):
    service = PersonalMediaService(personal_factory)
    service.save_review("movie", 1, 10, "Notum\n🎬")
    service.dismiss({"id": 1, "mediaType": "movie"}, True)
    transfer = TransferService(personal_factory)
    path = tmp_path / "personal.json"
    transfer.export_file(path)
    target = initialize_database(tmp_path / "import.sqlite3")
    try:
        factory = create_session_factory(target)
        TransferService(factory).import_file(path)
        imported = PersonalMediaService(factory)
        assert imported.read("movie", 1) == service.read("movie", 1)
        document = json.loads(path.read_text())
        row = next(
            row
            for row in document["tracking"]
            if row["tmdb_id"] == 1 and row["media_type"] == "MOVIE"
        )
        row.update(
            personal_rating=None,
            personal_note="",
            dismissed=False,
            updated_at="2099-01-01T00:00:00Z",
        )
        path.write_text(json.dumps(document))
        TransferService(factory).import_file(path)
        assert imported.read("movie", 1)["rating"] == 0
        assert imported.read("movie", 1)["note"] == ""
        assert imported.hidden() == []
    finally:
        target.dispose()


@pytest.mark.parametrize("version", [1, 2])
def test_old_backup_keeps_new_personal_fields(personal_factory, tmp_path, version):
    service = PersonalMediaService(personal_factory)
    service.save_review("movie", 1, 8, "Keep this")
    service.dismiss({"id": 1, "mediaType": "movie"}, True)
    transfer = TransferService(personal_factory)
    payload = transfer.build_export().model_dump(mode="json")
    payload["schema_version"] = version
    for row in payload["tracking"]:
        for field in ("personal_rating", "personal_note", "dismissed"):
            row.pop(field)
        row["updated_at"] = "2099-01-01T00:00:00Z"
        if version == 1:
            row.pop("sort_order")
    path = tmp_path / "old.json"
    path.write_text(json.dumps(payload))
    transfer.import_file(path)
    assert service.read("movie", 1)["rating"] == 8
    assert service.read("movie", 1)["note"] == "Keep this"
    assert service.read("movie", 1)["dismissed"]


@pytest.mark.parametrize("operation", ["review", "batch"])
def test_shutdown_drains_accepted_personal_writes(personal_factory, operation):
    QGuiApplication.instance() or QGuiApplication([])
    service = PersonalMediaService(personal_factory)
    controller = (
        PersonalMediaController(service)
        if operation == "review"
        else MovieLibraryController(
            MovieLibraryService(personal_factory), images=FakeImages()
        )
    )
    executor = (
        controller._writes if operation == "review" else controller._write_executor
    )
    entered, release = Event(), Event()

    def block():
        entered.set()
        assert release.wait(timeout=5)

    blocker = executor.submit(block)
    assert entered.wait(timeout=1)
    if operation == "review":
        controller.saveReview("movie", 1, 9, "queued")
    else:
        controller.batchApply([1, 2], "WATCHED", 0)
    closer = Thread(target=controller.close)
    closer.start()
    try:
        release.set()
        blocker.result(timeout=2)
        closer.join(timeout=3)
        assert not closer.is_alive()
        if operation == "review":
            assert service.read("movie", 1)["note"] == "queued"
        else:
            assert (
                MovieLibraryService(personal_factory)
                .snapshot(None, "custom")
                .items[0]
                .status
                == "WATCHED"
            )
    finally:
        release.set()
        closer.join(timeout=3)


@pytest.mark.parametrize("kind", ["movie", "tv"])
def test_dismissed_recommendations_are_filtered_without_changing_remote_cache(
    personal_factory, kind
):
    data = responses() if kind == "movie" else payloads()
    item_id = 42 if kind == "movie" else 77
    section = data[f"/3/{kind}/{item_id}/recommendations"]
    section["results"] = [
        {
            "id": value,
            "title": str(value),
            "original_title": str(value),
            "name": str(value),
            "original_name": str(value),
        }
        for value in (11, 12)
    ]
    section["total_results"] = 2
    personal = PersonalMediaService(personal_factory)
    summary = {"id": 11, "mediaType": kind, "title": "Dismissed"}
    personal.dismiss(summary, True)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=data[request.url.path])
        )
    ) as http:
        service_type = MovieDetailService if kind == "movie" else TvDetailService
        service = service_type(TmdbClient(http, token="test-only"), personal_factory)
        assert [row["id"] for row in service.load(item_id)["recommendations"]] == [12]
        with personal_factory() as session:
            media = MediaRepository(session).get_by_tmdb(
                item_id, MediaType(kind.upper())
            )
            assert len(media.metadata_json["recommendations"]["results"]) == 2
        personal.dismiss(summary, False)
        assert [row["id"] for row in service.cached(item_id)["recommendations"]] == [
            11,
            12,
        ]


def test_late_personal_read_cannot_overwrite_new_review(personal_factory):
    app = QGuiApplication.instance() or QGuiApplication([])
    entered, release = Event(), Event()

    class SlowService(PersonalMediaService):
        block = True

        def read(self, kind, item_id):
            record = super().read(kind, item_id)
            if self.block:
                self.block = False
                entered.set()
                assert release.wait(timeout=3)
            return record

    controller = PersonalMediaController(SlowService(personal_factory))
    try:
        controller.load("movie", 1)
        assert entered.wait(timeout=1)
        old_read = controller._future
        controller.saveReview("movie", 1, 9, "newer note")
        wait_for(
            app, lambda: not controller.busy and controller.current.get("rating") == 9
        )
        release.set()
        old_read.result(timeout=2)
        app.processEvents()
        assert controller.current["note"] == "newer note"
    finally:
        release.set()
        controller.close()


def test_late_discovery_page_respects_new_dismissal_and_restores_without_search(
    personal_factory,
):
    app = QGuiApplication.instance() or QGuiApplication([])
    prefs = PersonalMediaService(personal_factory)
    client = _DiscoverClient()
    controller = DiscoverController(
        client=client, images=FakeImages(), preferences=prefs
    )
    try:
        controller.applyFilters("movie", "", 0, "", 0, 100)
        wait_for(app, lambda: not controller.busy and bool(controller.items))
        old = list(controller.items)
        prefs.dismiss({"id": 10, "mediaType": "movie", "title": "Hidden"}, True)
        controller.refresh_preferences()
        wait_for(app, lambda: not controller.items)
        controller._apply_loaded(controller._generation, old, 1, 2, "")
        assert controller.items == []
        prefs.dismiss({"id": 10, "mediaType": "movie"}, False)
        controller.refresh_preferences()
        wait_for(app, lambda: bool(controller.items))
        assert len(client.calls) == 1
    finally:
        controller.close()
