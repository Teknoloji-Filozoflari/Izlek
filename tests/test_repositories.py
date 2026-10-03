"""Direct repository contracts on a real, migrated SQLite database."""

from datetime import date

import pytest

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import (
    CustomListRepository,
    EpisodeRepository,
    MediaRepository,
    SeasonRepository,
    UserMediaRepository,
)


@pytest.fixture
def database(tmp_path):
    engine = initialize_database(tmp_path / "repository.sqlite3")
    try:
        yield create_session_factory(engine)
    finally:
        engine.dispose()


def test_media_and_tracking_repository_contracts(database):
    with database.begin() as session:
        media = MediaRepository(session)
        users = UserMediaRepository(session)
        tracked = media.upsert(1, MediaType.MOVIE, "Tracked")
        favorite = media.upsert(2, MediaType.MOVIE, "Favorite")
        hidden = media.upsert(3, MediaType.MOVIE, "Hidden")

        users.set_status(tracked.id, TrackingStatus.PLANNED)
        users.set_status(tracked.id, TrackingStatus.WATCHING, manual=False)
        users.set_favorite(favorite.id, True)
        users.set_favorite(hidden.id, False)

        assert users.get(tracked.id).status == TrackingStatus.PLANNED
        assert users.get(tracked.id).status_is_manual is True
        local_tmdb_ids = [
            item.tmdb_id
            for item, _ in media.list_local_media(MediaType.MOVIE)
        ]
        assert local_tmdb_ids == [1, 2]
        assert users.remove(999_999) is False
        assert media.delete(999_999) is False

        with pytest.raises(ValueError, match="Bilinmeyen metadata"):
            media.upsert(4, MediaType.MOVIE, "Invalid", favorite=True)


def test_episode_progress_joined_reads_are_ordered_and_scoped(database):
    with database.begin() as session:
        media = MediaRepository(session)
        seasons = SeasonRepository(session)
        episodes = EpisodeRepository(session)
        first_show = media.upsert(10, MediaType.TV, "First")
        second_show = media.upsert(20, MediaType.TV, "Second")
        first_season = seasons.upsert(first_show.id, 2)
        earlier_season = seasons.upsert(first_show.id, 1)
        other_season = seasons.upsert(second_show.id, 1)
        later = episodes.upsert(first_season.id, 2, air_date=date(2024, 1, 2))
        earlier = episodes.upsert(first_season.id, 1, air_date=date(2024, 1, 1))
        first = episodes.upsert(earlier_season.id, 1, air_date=date(2023, 1, 1))
        episodes.upsert(other_season.id, 1, air_date=date(2022, 1, 1))
        episodes.set_watched(earlier.id, True)

        season_rows = episodes.list_for_season_with_progress(first_season.id)
        assert [episode.id for episode, _ in season_rows] == [earlier.id, later.id]
        watched_values = [
            progress.watched if progress else None
            for _, progress in season_rows
        ]
        assert watched_values == [True, None]

        show_rows = episodes.list_for_media_with_progress(first_show.id)
        assert [
            (season.season_number, episode.episode_number)
            for season, episode, _ in show_rows
        ] == [(1, 1), (2, 1), (2, 2)]
        assert show_rows[0][1].id == first.id
        candidates = episodes.list_continue_candidates({first_show.id})
        assert {row[0].id for row in candidates} == {first_show.id}

        deleted_episode_id = earlier.id
        assert episodes.delete(earlier.id) is True
        assert episodes.delete(earlier.id) is False

    with database() as session:
        assert EpisodeRepository(session).get_progress(deleted_episode_id) is None


def test_season_and_custom_list_repository_error_boundaries(database):
    with database.begin() as session:
        media = MediaRepository(session)
        show = media.upsert(30, MediaType.TV, "Show")
        movie = media.upsert(31, MediaType.MOVIE, "Movie")
        seasons = SeasonRepository(session)
        lists = CustomListRepository(session)

        with pytest.raises(LookupError, match="Medya bulunamadı"):
            seasons.upsert(999_999, 1)
        with pytest.raises(ValueError, match="diziye"):
            seasons.upsert(movie.id, 1)
        with pytest.raises(ValueError, match="Bilinmeyen metadata"):
            seasons.upsert(show.id, 1, unexpected=True)

        first = lists.create("First", 1)
        second = lists.create("Second", 0)
        lists.add_item(first.id, movie.id, 1)
        lists.add_item(second.id, movie.id, 0)
        assert [item.name for item in lists.list_all()] == ["Second", "First"]
        assert lists.list_names_for_media(movie.id) == ["Second", "First"]
        assert len(lists.list_all_items()) == 2

        with pytest.raises(LookupError, match="Liste bulunamadı"):
            lists.rename(999_999, "Missing")
        with pytest.raises(LookupError, match="Liste öğesi bulunamadı"):
            lists.set_item_position(first.id, show.id, 0)
        assert lists.remove_item(first.id, show.id) is False
        assert lists.delete(999_999) is False
