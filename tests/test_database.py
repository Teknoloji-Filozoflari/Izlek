"""Migration, constraint, and repository behavior on real SQLite files."""

from datetime import date
from stat import S_IMODE

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from izlek.db.engine import (
    create_database_engine,
    create_session_factory,
    database_path,
    initialize_database,
    upgrade_database,
)
from izlek.db.models import MediaItem, MediaType, TrackingStatus
from izlek.repositories import (
    CustomListRepository,
    EpisodeRepository,
    MediaRepository,
    SeasonRepository,
    UserMediaRepository,
)


@pytest.fixture
def database(tmp_path):
    engine = initialize_database(tmp_path / "data/izlek.sqlite3")
    try:
        yield engine
    finally:
        engine.dispose()


def test_auto_migration_and_xdg_location(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    path = database_path()
    assert path == tmp_path / "xdg-data/izlek/izlek.sqlite3"
    assert not path.exists()

    engine = initialize_database()
    try:
        assert path.is_file()
        assert S_IMODE(path.stat().st_mode) == 0o600
        tables = set(inspect(engine).get_table_names())
        assert tables == {
            "alembic_version",
            "media_item",
            "user_media",
            "season",
            "episode",
            "episode_progress",
            "custom_list",
            "custom_list_item",
        }
        assert "last_synced_at" in {
            column["name"] for column in inspect(engine).get_columns("season")
        }
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT version_num FROM alembic_version")
            ) == ("0003_season_freshness")
            assert connection.scalar(text("PRAGMA foreign_keys")) == 1
        upgrade_database(engine)
    finally:
        engine.dispose()


def test_migration_can_downgrade_and_reapply(database):
    from pathlib import Path

    import izlek.db.engine as db_engine

    config = Config()
    config.set_main_option(
        "script_location", str(Path(db_engine.__file__).parent / "migrations")
    )
    with database.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
    assert "media_item" not in inspect(database).get_table_names()
    upgrade_database(database)
    assert "media_item" in inspect(database).get_table_names()


def test_existing_status_is_preserved_as_manual_on_upgrade(tmp_path):
    from pathlib import Path

    import izlek.db.engine as db_engine

    engine = create_database_engine(tmp_path / "old.sqlite3")
    config = Config()
    config.set_main_option(
        "script_location", str(Path(db_engine.__file__).parent / "migrations")
    )
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "0001_initial")
            connection.execute(
                text(
                    "INSERT INTO media_item (id, tmdb_id, media_type, original_title) "
                    "VALUES (1, 77, 'TV', 'Old Show')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO user_media (media_id, status, favorite) "
                    "VALUES (1, 'WATCHED', 0)"
                )
            )
        upgrade_database(engine)
        with create_session_factory(engine)() as session:
            user = UserMediaRepository(session).get(1)
            assert user.status == TrackingStatus.WATCHED
            assert user.status_is_manual is True
    finally:
        engine.dispose()


def test_media_identity_and_constraints(database):
    sessions = create_session_factory(database)
    with sessions.begin() as session:
        repo = MediaRepository(session)
        movie = repo.upsert(
            42,
            MediaType.MOVIE,
            "Original Film",
            original_language="en",
            release_date=date(2024, 1, 2),
            metadata_json={"genres": [18]},
        )
        movie_id = movie.id
        assert repo.upsert(42, MediaType.MOVIE, "Retitled Film").id == movie_id
        assert repo.upsert(42, MediaType.TV, "Original Series").id != movie_id
        assert len(repo.list_all()) == 2
    with sessions() as session:
        movie = MediaRepository(session).get_by_tmdb(42, MediaType.MOVIE)
        assert movie.original_title == "Retitled Film"
        assert movie.release_date == date(2024, 1, 2)
        assert movie.metadata_json == {"genres": [18]}

    with pytest.raises(IntegrityError), sessions.begin() as session:
        session.add(
            MediaItem(tmdb_id=42, media_type=MediaType.MOVIE, original_title="X")
        )
        session.flush()
    with pytest.raises(IntegrityError), sessions.begin() as session:
        session.execute(
            text(
                "INSERT INTO media_item (tmdb_id, media_type, original_title) "
                "VALUES (999, 'BOOK', 'Invalid')"
            )
        )
    with pytest.raises(IntegrityError), sessions.begin() as session:
        session.execute(
            text(
                "INSERT INTO user_media (media_id, status) "
                "VALUES (:media_id, 'DROPPED')"
            ),
            {"media_id": movie_id},
        )


def test_tracking_and_episode_progress_survive_metadata_refresh(database):
    sessions = create_session_factory(database)
    with sessions.begin() as session:
        media = MediaRepository(session).upsert(100, MediaType.TV, "Series")
        media_id = media.id
        tracking = UserMediaRepository(session)
        tracking.set_favorite(media_id, True)
        tracking.set_status(media_id, TrackingStatus.WATCHING)
        assert tracking.get(media_id).status_is_manual is True
        season = SeasonRepository(session).upsert(media_id, 1, name="Season One")
        episode = EpisodeRepository(session).upsert(season.id, 1, name="Pilot")
        episode_id = episode.id
        EpisodeRepository(session).set_watched(episode_id, True)

    with sessions.begin() as session:
        MediaRepository(session).upsert(100, MediaType.TV, "Renamed Series")
        season = SeasonRepository(session).upsert(media_id, 1, name="New Season Name")
        EpisodeRepository(session).upsert(season.id, 1, name="New Episode Name")
        assert UserMediaRepository(session).get(media_id).favorite is True
        assert UserMediaRepository(session).get(media_id).status == (
            TrackingStatus.WATCHING
        )
        progress = EpisodeRepository(session).get_progress(episode_id)
        assert progress.watched is True
        assert progress.watched_at is not None
        EpisodeRepository(session).set_watched(episode_id, False)
        assert progress.watched_at is None
        UserMediaRepository(session).set_status(media_id, None)
        assert UserMediaRepository(session).get(media_id).favorite is True
        assert UserMediaRepository(session).get(media_id).status_is_manual is False


def test_lists_crud_ordering_and_cascade(database):
    sessions = create_session_factory(database)
    with sessions.begin() as session:
        media_repo = MediaRepository(session)
        first = media_repo.upsert(1, MediaType.MOVIE, "One")
        second = media_repo.upsert(2, MediaType.MOVIE, "Two")
        lists = CustomListRepository(session)
        weekend = lists.create("Hafta Sonu", sort_order=2)
        favorites = lists.create("Favoriler", sort_order=1)
        weekend_id, favorites_id = weekend.id, favorites.id
        first_id, second_id = first.id, second.id
        lists.add_item(weekend_id, first_id, sort_order=2)
        lists.add_item(weekend_id, second_id, sort_order=1)
        lists.add_item(favorites_id, first_id)
        assert [item.id for item in lists.list_all()] == [favorites_id, weekend_id]
        assert [item.media_id for item in lists.list_items(weekend_id)] == [
            second_id,
            first_id,
        ]
        lists.add_item(weekend_id, first_id, sort_order=0)
        assert len(lists.list_items(weekend_id)) == 2
        lists.rename(weekend_id, "Yeni Ad")
        lists.set_position(weekend_id, 0)
        lists.set_item_position(weekend_id, second_id, 3)
        assert lists.remove_item(favorites_id, first_id)
        assert lists.delete(favorites_id)
        assert media_repo.delete(first_id)

    with sessions() as session:
        lists = CustomListRepository(session)
        assert lists.get(weekend_id).name == "Yeni Ad"
        assert [item.media_id for item in lists.list_items(weekend_id)] == [second_id]
        assert MediaRepository(session).get(first_id) is None
        assert session.scalar(select(MediaItem).where(MediaItem.id == second_id))


def test_seasons_only_belong_to_tv(database):
    sessions = create_session_factory(database)
    with sessions.begin() as session:
        movie = MediaRepository(session).upsert(3, MediaType.MOVIE, "Film")
        with pytest.raises(ValueError, match="diziye"):
            SeasonRepository(session).upsert(movie.id, 1)
