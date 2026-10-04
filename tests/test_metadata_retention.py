"""Remote expiry must preserve every personal row and fresh season."""

from datetime import datetime, timedelta

from sqlalchemy import select

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import Episode, MediaItem, MediaType, Season, TrackingStatus
from izlek.repositories.local import (
    CustomListRepository,
    EpisodeRepository,
    MediaRepository,
    SeasonRepository,
    UserMediaRepository,
)
from izlek.services.metadata_retention import (
    MetadataRetentionService,
    merge_remote_metadata,
)
from izlek.services.transfer import TransferService


def test_expiry_preserves_personal_data_and_recent_season_metadata(tmp_path):
    engine = initialize_database(tmp_path / "state.sqlite3")
    factory = create_session_factory(engine)
    now = datetime(2026, 10, 4)
    old = now - timedelta(days=181)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(
            77,
            MediaType.TV,
            "Old show",
            overview="Old overview",
            last_synced_at=old,
            metadata_json={"providers": {"id": 77}},
        )
        users = UserMediaRepository(session)
        users.set_status(media.id, TrackingStatus.WATCHING)
        users.set_favorite(media.id, True)
        old_season = SeasonRepository(session).upsert(
            media.id,
            1,
            name="Old season",
            last_synced_at=old,
        )
        recent_season = SeasonRepository(session).upsert(
            media.id,
            2,
            name="Fresh season",
            last_synced_at=now,
        )
        episodes = EpisodeRepository(session)
        old_episode = episodes.upsert(old_season.id, 1, name="Old pilot", runtime=42)
        episodes.set_watched(old_episode.id, True)
        episodes.upsert(recent_season.id, 1, name="Fresh pilot", runtime=50)
        lists = CustomListRepository(session)
        custom_list = lists.create("My list")
        lists.add_item(custom_list.id, media.id)
    transfer = TransferService(factory)
    before = transfer.build_export().model_dump(mode="json")
    service = MetadataRetentionService(factory)
    try:
        assert service.prune(now=now) == 3
        after = transfer.build_export().model_dump(mode="json")
        for section in ("tracking", "episodes", "favorites", "lists"):
            assert after[section] == before[section]
        assert after["media"][0]["original_title"] == "Dizi #77"
        assert after["media"][0]["metadata"] is None
        with factory() as session:
            assert session.get(Episode, old_episode.id).name is None
            assert session.get(Season, old_season.id).last_synced_at is None
            assert session.get(Season, recent_season.id).name == "Fresh season"
        assert service.prune(now=now) == 0
    finally:
        engine.dispose()


def test_failed_optional_endpoint_does_not_gain_a_new_cache_timestamp(tmp_path):
    engine = initialize_database(tmp_path / "state.sqlite3")
    factory = create_session_factory(engine)
    now = datetime(2026, 10, 4)
    yesterday = now - timedelta(days=1)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(
            42,
            MediaType.MOVIE,
            "Film",
            last_synced_at=yesterday,
            metadata_json={"providers": {"id": 42}},
        )
        first = merge_remote_metadata(media, {"detail": {"id": 42}}, now)
        assert first["_section_synced_at"]["providers"] == yesterday.isoformat()
        media.metadata_json = first
        media.last_synced_at = now
        later = merge_remote_metadata(
            media, {"detail": {"id": 42}}, now + timedelta(days=180)
        )
        assert "providers" not in later
        assert "providers" not in later["_section_synced_at"]
    engine.dispose()


def test_optional_expiry_does_not_clear_recent_main_metadata(tmp_path):
    engine = initialize_database(tmp_path / "state.sqlite3")
    factory = create_session_factory(engine)
    now = datetime(2026, 10, 4)
    with factory.begin() as session:
        MediaRepository(session).upsert(
            42,
            MediaType.MOVIE,
            "Fresh title",
            last_synced_at=now,
            metadata_json={
                "detail": {"id": 42},
                "providers": {"id": 42},
                "_section_synced_at": {
                    "providers": (now - timedelta(days=181)).isoformat()
                },
            },
        )
    try:
        assert MetadataRetentionService(factory).prune(now=now) == 1
        with factory() as session:
            media = session.scalar(select(MediaItem))
            assert media.original_title == "Fresh title"
            assert media.metadata_json["detail"] == {"id": 42}
            assert "providers" not in media.metadata_json
    finally:
        engine.dispose()
