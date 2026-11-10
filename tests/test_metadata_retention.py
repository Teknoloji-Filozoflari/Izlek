"""Remote expiry must preserve every personal row and fresh season."""

from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select, text

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
    METADATA_RETENTION,
    MetadataRetentionService,
    merge_remote_metadata,
)
from izlek.services.movie_detail import MovieDetailService
from izlek.services.transfer import TransferService
from izlek.services.tv_detail import TvDetailService
from izlek.tmdb.client import NetworkError, TmdbClient


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
        old_episode = episodes.upsert(
            old_season.id, 1, name="Old pilot", runtime=42, last_synced_at=old
        )
        episodes.set_watched(old_episode.id, True)
        episodes.upsert(
            recent_season.id, 1, name="Fresh pilot", runtime=50, last_synced_at=now
        )
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
            assert session.get(Episode, old_episode.id).last_synced_at is None
            assert session.get(Season, old_season.id).last_synced_at is None
            assert session.get(Season, recent_season.id).name == "Fresh season"
            assert session.execute(text("PRAGMA integrity_check")).scalar() == "ok"
        assert service.prune(now=now) == 0
    finally:
        engine.dispose()


def test_retention_boundary_keeps_day_179_and_clears_day_180(tmp_path):
    engine = initialize_database(tmp_path / "boundary.sqlite3")
    factory = create_session_factory(engine)
    now = datetime(2026, 11, 10, 12, 0, 0)
    keep_at = now - METADATA_RETENTION + timedelta(seconds=1)
    clear_at = now - METADATA_RETENTION
    with factory.begin() as session:
        MediaRepository(session).upsert(
            1,
            MediaType.MOVIE,
            "Keep",
            overview="still fresh",
            last_synced_at=keep_at,
            metadata_json={"detail": {"id": 1}},
        )
        MediaRepository(session).upsert(
            2,
            MediaType.MOVIE,
            "Clear",
            overview="expired",
            last_synced_at=clear_at,
            metadata_json={"detail": {"id": 2}},
        )
    try:
        assert MetadataRetentionService(factory).prune(now=now) == 1
        with factory() as session:
            keep = MediaRepository(session).get_by_tmdb(1, MediaType.MOVIE)
            clear = MediaRepository(session).get_by_tmdb(2, MediaType.MOVIE)
            assert keep.overview == "still fresh"
            assert keep.metadata_json == {"detail": {"id": 1}}
            assert clear.overview is None
            assert clear.metadata_json is None
            assert clear.original_title == "Film #2"
            assert clear.last_synced_at is None
        assert MetadataRetentionService(factory).prune(now=now) == 0
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


def test_import_of_old_metadata_is_skipped_while_personal_data_imports(tmp_path):
    source_engine = initialize_database(tmp_path / "source.sqlite3")
    target_engine = initialize_database(tmp_path / "target.sqlite3")
    source = create_session_factory(source_engine)
    target = create_session_factory(target_engine)
    now = datetime(2026, 11, 10)
    old = now - timedelta(days=200)
    with source.begin() as session:
        media = MediaRepository(session).upsert(
            55,
            MediaType.TV,
            "Ancient show",
            overview="stale overview",
            poster_path="/old.jpg",
            last_synced_at=old,
            metadata_json={"origin_country": ["TR"]},
        )
        media.created_at = old
        media.updated_at = old
        users = UserMediaRepository(session)
        users.set_status(media.id, TrackingStatus.WATCHING)
        users.set_favorite(media.id, True)
        season = SeasonRepository(session).upsert(
            media.id, 1, name="S1", last_synced_at=old
        )
        episode = EpisodeRepository(session).upsert(
            season.id, 1, name="Pilot", last_synced_at=old
        )
        EpisodeRepository(session).set_watched(episode.id, True)
        lists = CustomListRepository(session)
        custom = lists.create("Keep me")
        lists.add_item(custom.id, media.id)
    export_path = Path(tmp_path / "old.json")
    TransferService(source).export_file(export_path)
    # Rewrite exported timestamps so the file is unambiguously past retention.
    document = TransferService(source).build_export(exported_at=now)
    payload = document.model_dump(mode="json")
    payload["media"][0]["last_synced_at"] = old.isoformat() + "Z"
    payload["media"][0]["created_at"] = old.isoformat() + "Z"
    payload["media"][0]["seasons"][0]["last_synced_at"] = old.isoformat() + "Z"
    payload["media"][0]["seasons"][0]["episodes"][0]["last_synced_at"] = (
        old.isoformat() + "Z"
    )
    export_path.write_text(
        __import__("json").dumps(payload),
        encoding="utf-8",
    )
    service = TransferService(target)
    try:
        preview = service.preview_file(export_path)
        assert preview["metadata_skipped"] >= 1
        report = service.import_file(export_path)
        assert report["metadata_skipped"] >= 1
        assert report["tracking_merged"] == 1
        assert report["episode_progress_merged"] == 1
        with target() as session:
            item = MediaRepository(session).get_by_tmdb(55, MediaType.TV)
            assert item.overview is None
            assert item.metadata_json is None
            assert item.original_title == "Dizi #55"
            user = UserMediaRepository(session).get(item.id)
            assert user.status == TrackingStatus.WATCHING
            assert user.favorite is True
            season = SeasonRepository(session).list_for_media(item.id)[0]
            assert season.name is None
            episode = EpisodeRepository(session).list_for_season(season.id)[0]
            assert episode.name is None
            assert EpisodeRepository(session).get_progress(episode.id).watched is True
            lists = CustomListRepository(session).list_all()
            assert lists[0].name == "Keep me"
            assert session.execute(text("PRAGMA integrity_check")).scalar() == "ok"
    finally:
        source_engine.dispose()
        target_engine.dispose()


def test_offline_expired_detail_keeps_personal_state_and_refreshes_online(tmp_path):
    engine = initialize_database(tmp_path / "offline.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(
            9,
            MediaType.MOVIE,
            "Film #9",
            last_synced_at=None,
            metadata_json=None,
        )
        users = UserMediaRepository(session)
        users.set_status(media.id, TrackingStatus.WATCHED)
        users.set_favorite(media.id, True)

    class OfflineClient(TmdbClient):
        def movie(self, movie_id: int):  # type: ignore[override]
            raise NetworkError("offline")

    offline = MovieDetailService(OfflineClient(), factory)
    try:
        cached = offline.cached(9)
        assert cached is not None
        assert cached["metadataExpired"] is True
        assert cached["status"] == "WATCHED"
        assert cached["favorite"] is True
        assert offline.needs_refresh(9) is True
    finally:
        offline.close()

    class OnlineClient(TmdbClient):
        def movie(self, movie_id: int):  # type: ignore[override]
            from izlek.tmdb.models import MovieDetail

            return MovieDetail.model_validate(
                {
                    "id": movie_id,
                    "title": "Restored",
                    "original_title": "Restored",
                    "overview": "back online",
                    "original_language": "en",
                }
            )

        def movie_credits(self, movie_id: int):  # type: ignore[override]
            from izlek.tmdb.models import MovieCredits

            return MovieCredits.model_validate({"id": movie_id, "cast": [], "crew": []})

        def movie_videos(self, movie_id: int):  # type: ignore[override]
            from izlek.tmdb.models import MovieVideos

            return MovieVideos.model_validate({"id": movie_id, "results": []})

        def movie_similar(self, movie_id: int):  # type: ignore[override]
            from izlek.tmdb.models import MovieSearchResults

            return MovieSearchResults.model_validate(
                {"page": 1, "results": [], "total_pages": 1, "total_results": 0}
            )

        def movie_recommendations(self, movie_id: int):  # type: ignore[override]
            from izlek.tmdb.models import MovieSearchResults

            return MovieSearchResults.model_validate(
                {"page": 1, "results": [], "total_pages": 1, "total_results": 0}
            )

        def movie_watch_providers(self, movie_id: int):  # type: ignore[override]
            from izlek.tmdb.models import MovieWatchProviders

            return MovieWatchProviders.model_validate({"id": movie_id, "results": {}})

    online = MovieDetailService(OnlineClient(), factory)
    try:
        detail = online.load(9)
        assert detail["title"] == "Restored"
        assert detail["status"] == "WATCHED"
        assert detail["favorite"] is True
        assert detail.get("metadataExpired") is not True
        with factory() as session:
            item = MediaRepository(session).get_by_tmdb(9, MediaType.MOVIE)
            assert item.last_synced_at is not None
            assert item.overview == "back online"
    finally:
        online.close()
        engine.dispose()


def test_prune_does_not_delete_episode_or_progress_rows(tmp_path):
    engine = initialize_database(tmp_path / "cascade.sqlite3")
    factory = create_session_factory(engine)
    now = datetime(2026, 11, 10)
    old = now - timedelta(days=200)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(
            3, MediaType.TV, "Show", last_synced_at=old
        )
        media.created_at = old
        season = SeasonRepository(session).upsert(
            media.id, 1, name="S1", last_synced_at=old
        )
        episode = EpisodeRepository(session).upsert(
            season.id, 1, name="E1", last_synced_at=old
        )
        EpisodeRepository(session).set_watched(episode.id, True)
        episode_id = episode.id
        season_id = season.id
        media_id = media.id
    MetadataRetentionService(factory).prune(now=now)
    with factory() as session:
        assert session.get(MediaItem, media_id) is not None
        assert session.get(Season, season_id) is not None
        assert session.get(Episode, episode_id) is not None
        assert EpisodeRepository(session).get_progress(episode_id).watched is True
        assert session.get(Episode, episode_id).name is None
    engine.dispose()


def test_tv_expired_shell_keeps_progress(tmp_path):
    engine = initialize_database(tmp_path / "tv-shell.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        media = MediaRepository(session).upsert(11, MediaType.TV, "Dizi #11")
        UserMediaRepository(session).set_status(media.id, TrackingStatus.WATCHING)
        season = SeasonRepository(session).upsert(media.id, 1)
        episode = EpisodeRepository(session).upsert(season.id, 1)
        EpisodeRepository(session).set_watched(episode.id, True)
    service = TvDetailService(TmdbClient(), factory)
    try:
        cached = service.cached(11)
        assert cached["metadataExpired"] is True
        assert cached["status"] == "WATCHING"
        assert cached["watchedEpisodeCount"] == 1
        assert cached["seasons"][0]["number"] == 1
    finally:
        service.close()
        engine.dispose()
