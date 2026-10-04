"""Portable İzlek JSON round trips and deterministic merge behavior."""

import json
from datetime import UTC, date, datetime
from stat import S_IMODE

import pytest
from sqlalchemy import func, select

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import (
    CustomList,
    CustomListItem,
    Episode,
    EpisodeProgress,
    MediaItem,
    MediaType,
    Season,
    TrackingStatus,
    UserMedia,
)
from izlek.repositories import (
    CustomListRepository,
    EpisodeRepository,
    MediaRepository,
    SeasonRepository,
    UserMediaRepository,
)
from izlek.repositories.local import TransferRepository
from izlek.services.transfer import TransferError, TransferService


def _seed_full_state(factory) -> None:
    timestamp = datetime(2025, 5, 6, 7, 8, 9)
    watched_at = datetime(2025, 5, 7, 8, 9, 10)
    with factory.begin() as session:
        media = MediaRepository(session)
        users = UserMediaRepository(session)
        seasons = SeasonRepository(session)
        episodes = EpisodeRepository(session)
        lists = CustomListRepository(session)

        movie = media.upsert(
            101,
            MediaType.MOVIE,
            "Portable Film",
            original_language="tr",
            overview="Film özeti",
            poster_path="/poster.jpg",
            release_date=date(2024, 2, 3),
            runtime=123,
            metadata_json={
                "genres": [{"id": 18, "name": "Drama"}],
                "access_token": "export-edilmemeli",
                "nested": {"cache_path": "/tmp/private-cache", "vote": 8.2},
            },
            last_synced_at=timestamp,
        )
        show = media.upsert(
            202,
            MediaType.TV,
            "Portable Show",
            original_language="en",
            first_air_date=date(2023, 4, 5),
            metadata_json={"origin_country": ["TR"]},
            last_synced_at=timestamp,
        )
        movie.created_at = timestamp
        movie.updated_at = timestamp
        show.created_at = timestamp
        show.updated_at = timestamp

        movie_state = users.set_status(movie.id, TrackingStatus.WATCHED)
        users.set_favorite(movie.id, True)
        movie_state.added_at = timestamp
        movie_state.updated_at = timestamp
        show_state = users.set_status(show.id, TrackingStatus.WATCHING)
        show_state.added_at = timestamp
        show_state.updated_at = timestamp

        season = seasons.upsert(
            show.id,
            1,
            tmdb_season_id=303,
            name="Season 1",
            overview="Season overview",
            poster_path="/season.jpg",
            air_date=date(2023, 4, 5),
            last_synced_at=timestamp,
        )
        first_episode = episodes.upsert(
            season.id,
            1,
            tmdb_episode_id=404,
            name="Pilot",
            overview="Episode overview",
            air_date=date(2023, 4, 5),
            runtime=48,
            still_path="/still.jpg",
        )
        episodes.upsert(
            season.id,
            2,
            tmdb_episode_id=405,
            name="Second",
            runtime=51,
        )
        progress = episodes.set_watched(first_episode.id, True)
        progress.watched_at = watched_at

        weekend = lists.create("Hafta Sonu", 0)
        archive = lists.create("Arşiv", 1)
        weekend.created_at = timestamp
        archive.created_at = timestamp
        first_member = lists.add_item(weekend.id, show.id, 0)
        second_member = lists.add_item(weekend.id, movie.id, 1)
        third_member = lists.add_item(archive.id, movie.id, 0)
        for member in (first_member, second_member, third_member):
            member.added_at = timestamp


def _portable_sections(document) -> dict:
    payload = document.model_dump(mode="json")
    return {
        key: payload[key]
        for key in ("media", "tracking", "episodes", "favorites", "lists")
    }


def test_export_import_round_trip_preserves_equivalent_user_state(tmp_path):
    source_engine = initialize_database(tmp_path / "source.sqlite3")
    target_engine = initialize_database(tmp_path / "target.sqlite3")
    source_factory = create_session_factory(source_engine)
    target_factory = create_session_factory(target_engine)
    _seed_full_state(source_factory)
    source = TransferService(source_factory)
    target = TransferService(target_factory)
    export_path = tmp_path / "izlek-export.json"

    try:
        expected = source.build_export(
            exported_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
        )
        report = source.export_file(export_path)
        raw = export_path.read_text(encoding="utf-8")
        payload = json.loads(raw)

        assert set(payload) == {
            "schema_version",
            "exported_at",
            "app_version",
            "media",
            "tracking",
            "episodes",
            "favorites",
            "lists",
        }
        assert payload["schema_version"] == 1
        assert "export-edilmemeli" not in raw
        assert "/tmp/private-cache" not in raw
        assert report["media"] == 2
        assert report["episode_progress"] == 1

        import_report = target.import_file(export_path)
        actual = target.build_export(exported_at=expected.exported_at)

        assert import_report == {
            "media_created": 2,
            "media_merged": 0,
            "tracking_merged": 2,
            "episode_progress_merged": 1,
            "lists_created": 2,
            "lists_merged": 0,
            "list_items_added": 3,
            "list_items_existing": 0,
        }
        assert _portable_sections(actual) == _portable_sections(expected)
    finally:
        source.close()
        target.close()
        source_engine.dispose()
        target_engine.dispose()


def test_repeated_import_merges_identity_lists_and_keeps_watched_progress(tmp_path):
    source_engine = initialize_database(tmp_path / "source.sqlite3")
    target_engine = initialize_database(tmp_path / "target.sqlite3")
    source_factory = create_session_factory(source_engine)
    target_factory = create_session_factory(target_engine)
    _seed_full_state(source_factory)
    source = TransferService(source_factory)
    target = TransferService(target_factory)
    export_path = tmp_path / "state.json"
    source.export_file(export_path)

    try:
        target.import_file(export_path)
        with target_factory.begin() as session:
            progress = session.scalar(select(EpisodeProgress))
            progress.watched = True
            progress.watched_at = datetime(2026, 6, 1)
            custom_list = session.scalar(
                select(CustomList).where(CustomList.name == "Hafta Sonu")
            )
            custom_list.name = "HAFTA SONU"

        report = target.import_file(export_path)

        with target_factory() as session:
            assert session.scalar(select(func.count()).select_from(MediaItem)) == 2
            assert session.scalar(select(func.count()).select_from(UserMedia)) == 2
            assert session.scalar(select(func.count()).select_from(CustomList)) == 2
            assert session.scalar(select(func.count()).select_from(CustomListItem)) == 3
            progress = session.scalar(select(EpisodeProgress))
            assert progress.watched is True
            assert progress.watched_at == datetime(2026, 6, 1)
        assert report["lists_created"] == 0
        assert report["lists_merged"] == 2
        assert report["list_items_existing"] == 3
    finally:
        source.close()
        target.close()
        source_engine.dispose()
        target_engine.dispose()


def test_import_rejects_newer_or_broken_schema_before_writing(tmp_path):
    engine = initialize_database(tmp_path / "target.sqlite3")
    service = TransferService(create_session_factory(engine))
    future = tmp_path / "future.json"
    future.write_text('{"schema_version": 999}', encoding="utf-8")
    broken = tmp_path / "broken.json"
    broken.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "exported_at": "2026-01-01T00:00:00Z",
                "app_version": "1.0",
                "media": [],
                "tracking": [],
                "episodes": [],
                "favorites": [{"tmdb_id": 1, "media_type": "MOVIE"}],
                "lists": [],
            }
        ),
        encoding="utf-8",
    )

    try:
        with pytest.raises(TransferError, match="daha yeni"):
            service.import_file(future)
        with pytest.raises(TransferError, match="Medya referansı"):
            service.import_file(broken)
        with create_session_factory(engine)() as session:
            assert session.scalar(select(func.count()).select_from(MediaItem)) == 0
    finally:
        service.close()
        engine.dispose()


def test_export_adds_json_suffix_and_uses_private_permissions(tmp_path):
    engine = initialize_database(tmp_path / "source.sqlite3")
    service = TransferService(create_session_factory(engine))
    requested = tmp_path / "backups/izlek-state"
    target = requested.with_suffix(".json")
    try:
        report = service.export_file(requested)

        assert target.is_file()
        assert not requested.exists()
        assert S_IMODE(target.stat().st_mode) == 0o600
        assert report["media"] == 0
        assert report["bytes"] == target.stat().st_size
    finally:
        service.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not-json", "geçerli JSON değil"),
        ("[]", "JSON object"),
        ('{"schema_version": false}', "schema_version"),
        ('{"schema_version": 0}', "migration"),
    ],
)
def test_import_file_errors_are_safe_and_specific(tmp_path, content, message):
    engine = initialize_database(tmp_path / "target.sqlite3")
    service = TransferService(create_session_factory(engine))
    path = tmp_path / "invalid.json"
    path.write_text(content, encoding="utf-8")
    try:
        with pytest.raises(TransferError, match=message):
            service.read_file(path)
        with pytest.raises(TransferError, match="bulunamadı"):
            service.read_file(tmp_path / "missing.json")
    finally:
        service.close()
        engine.dispose()


def test_old_import_keeps_newer_episode_metadata_and_restores_missing_rows(tmp_path):
    engine = initialize_database(tmp_path / "state.sqlite3")
    factory = create_session_factory(engine)
    _seed_full_state(factory)
    service = TransferService(factory)
    path = tmp_path / "old.json"
    service.export_file(path)
    try:
        with factory.begin() as session:
            season = session.scalar(select(Season))
            season.last_synced_at = datetime(2026, 10, 4)
            first = session.scalar(select(Episode).where(Episode.episode_number == 1))
            first.name = "New episode title"
            first.runtime = 60
            second = session.scalar(select(Episode).where(Episode.episode_number == 2))
            session.delete(second)
        service.import_file(path)
        with factory() as session:
            episodes = list(
                session.scalars(select(Episode).order_by(Episode.episode_number))
            )
            assert [(item.name, item.runtime) for item in episodes] == [
                ("New episode title", 60),
                ("Second", 51),
            ]
            assert session.scalar(select(EpisodeProgress)).watched is True
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "problem", ["credits", "identity", "season", "episode", "name"]
)
def test_preview_rejects_unusable_metadata_before_database_write(tmp_path, problem):
    engine = initialize_database(tmp_path / "source.sqlite3")
    target_engine = initialize_database(tmp_path / "target.sqlite3")
    factory = create_session_factory(engine)
    _seed_full_state(factory)
    document = TransferService(factory).build_export().model_dump(mode="json")
    if problem == "credits":
        document["media"][0]["metadata"] = {"credits": {"id": 101, "cast": [{}]}}
    elif problem == "identity":
        document["media"][0]["metadata"] = {
            "detail": {"id": 999, "title": "Other", "original_title": "Other"}
        }
    elif problem == "season":
        document["media"][1]["seasons"] *= 2
    elif problem == "episode":
        document["media"][1]["seasons"][0]["episodes"] *= 2
    else:
        document["lists"][0]["name"] = "   "
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    target = TransferService(create_session_factory(target_engine))
    try:
        with pytest.raises(TransferError, match="Şema doğrulanamadı"):
            target.preview_file(path)
        with create_session_factory(target_engine)() as session:
            assert session.scalar(select(func.count()).select_from(MediaItem)) == 0
    finally:
        engine.dispose()
        target_engine.dispose()


def test_export_reads_one_snapshot_during_concurrent_status_change(
    tmp_path, monkeypatch
):
    engine = initialize_database(tmp_path / "state.sqlite3")
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        movie = MediaRepository(session).upsert(42, MediaType.MOVIE, "Film")
        UserMediaRepository(session).set_status(movie.id, TrackingStatus.PLANNED)
    original_read = TransferRepository.media

    def read_and_change(repository):
        rows = original_read(repository)
        with factory.begin() as writer:
            UserMediaRepository(writer).set_status(movie.id, TrackingStatus.WATCHED)
        return rows

    monkeypatch.setattr(TransferRepository, "media", read_and_change)
    try:
        document = TransferService(factory).build_export()
        assert document.tracking[0].status == "PLANNED"
        with factory() as session:
            assert (
                UserMediaRepository(session).get(movie.id).status
                == TrackingStatus.WATCHED
            )
    finally:
        engine.dispose()
