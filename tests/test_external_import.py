"""Trakt JSON and Letterboxd CSV adapters feed TransferService merges."""

import json
from datetime import date

from sqlalchemy import func, select

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import (
    EpisodeProgress,
    MediaItem,
    MediaType,
    TrackingStatus,
    UserMedia,
)
from izlek.repositories.local import UserMediaRepository
from izlek.services.import_adapters import letterboxd_to_export, trakt_to_export
from izlek.services.transfer import TransferError, TransferService


def test_trakt_watched_movies_and_shows_import(tmp_path):
    payload = [
        {
            "plays": 2,
            "last_watched_at": "2024-05-01T20:00:00.000Z",
            "movie": {
                "title": "Batman Begins",
                "year": 2005,
                "ids": {"trakt": 1, "tmdb": 272},
            },
        },
        {
            "plays": 3,
            "last_watched_at": "2024-06-02T12:00:00.000Z",
            "show": {
                "title": "Breaking Bad",
                "year": 2008,
                "ids": {"trakt": 1, "tmdb": 1396},
            },
            "seasons": [
                {
                    "number": 1,
                    "episodes": [
                        {
                            "number": 1,
                            "plays": 1,
                            "last_watched_at": "2024-06-01T12:00:00.000Z",
                        },
                        {
                            "number": 2,
                            "plays": 1,
                            "last_watched_at": "2024-06-02T12:00:00.000Z",
                        },
                    ],
                }
            ],
        },
        {
            "listed_at": "2024-07-01T00:00:00.000Z",
            "movie": {
                "title": "No TMDb",
                "year": 1999,
                "ids": {"trakt": 9, "imdb": "tt0000001"},
            },
        },
    ]
    path = tmp_path / "watched-movies.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    engine = initialize_database(tmp_path / "target.sqlite3")
    service = TransferService(create_session_factory(engine))
    try:
        preview = service.preview_file(path)
        assert preview["source"] == "trakt"
        assert preview["movies"] == 1
        assert preview["shows"] == 1
        assert preview["episode_progress"] == 2
        assert preview["skipped"] == 1

        report = service.import_file(path)
        assert report["media_created"] == 2
        assert report["episode_progress_merged"] == 2
        assert report["skipped"] == 1

        with create_session_factory(engine)() as session:
            movie = session.scalar(
                select(MediaItem).where(
                    MediaItem.tmdb_id == 272, MediaItem.media_type == MediaType.MOVIE
                )
            )
            show = session.scalar(
                select(MediaItem).where(
                    MediaItem.tmdb_id == 1396, MediaItem.media_type == MediaType.TV
                )
            )
            assert movie.original_title == "Batman Begins"
            assert movie.release_date == date(2005, 1, 1)
            movie_state = UserMediaRepository(session).get(movie.id)
            show_state = UserMediaRepository(session).get(show.id)
            assert movie_state.status == TrackingStatus.WATCHED
            assert show_state.status == TrackingStatus.WATCHING
            progress_count = session.scalar(
                select(func.count()).select_from(EpisodeProgress)
            )
            assert progress_count == 2
    finally:
        service.close()
        engine.dispose()


def test_trakt_history_and_ratings_adapters():
    history = [
        {
            "watched_at": "2023-01-02T03:04:05.000Z",
            "action": "watch",
            "type": "movie",
            "movie": {"title": "Heat", "year": 1995, "ids": {"tmdb": 949}},
        },
        {
            "watched_at": "2023-02-03T04:05:06.000Z",
            "action": "watch",
            "type": "episode",
            "episode": {
                "season": 1,
                "number": 1,
                "title": "Pilot",
                "ids": {"tmdb": 62085},
            },
            "show": {"title": "Breaking Bad", "ids": {"tmdb": 1396}},
        },
    ]
    ratings = [
        {
            "rated_at": "2023-03-04T05:06:07.000Z",
            "rating": 9,
            "type": "movie",
            "movie": {"title": "Heat", "year": 1995, "ids": {"tmdb": 949}},
        }
    ]
    watched = trakt_to_export(history)
    rated = trakt_to_export(ratings)
    assert watched.source == "trakt"
    assert {(item.media_type, item.tmdb_id) for item in watched.document.media} == {
        ("MOVIE", 949),
        ("TV", 1396),
    }
    assert len(watched.document.episodes) == 1
    assert rated.document.tracking[0].personal_rating == 9
    assert rated.document.tracking[0].status == "WATCHED"


def test_letterboxd_csv_import_requires_tmdb_and_maps_ratings(tmp_path):
    missing = tmp_path / "diary.csv"
    missing.write_text(
        "Date,Name,Year,Letterboxd URI,Rating,Watched Date\n"
        "2024-01-01,Heat,1995,https://boxd.it/29qU,4.5,2024-01-01\n",
        encoding="utf-8",
    )
    engine = initialize_database(tmp_path / "target.sqlite3")
    service = TransferService(create_session_factory(engine))
    try:
        try:
            service.preview_file(missing)
            raise AssertionError("tmdbID olmadan Letterboxd CSV kabul edilmemeli")
        except TransferError as exc:
            assert "tmdbID" in str(exc)

        path = tmp_path / "watched.csv"
        path.write_text(
            "tmdbID,Title,Year,Rating,WatchedDate,Review,List\n"
            "949,Heat,1995,4.5,2024-01-02,Harika film,Favoriler\n"
            "272,Batman Begins,2005,5,2024-02-03,,\n"
            ",Broken,2000,3,2024-03-04,,\n",
            encoding="utf-8",
        )
        preview = service.preview_file(path)
        assert preview["source"] == "letterboxd"
        assert preview["movies"] == 2
        assert preview["lists"] == 1
        assert preview["skipped"] == 1

        report = service.import_file(path)
        assert report["media_created"] == 2
        assert report["lists_created"] == 1
        assert report["list_items_added"] == 1

        with create_session_factory(engine)() as session:
            heat = session.scalar(
                select(MediaItem).where(MediaItem.tmdb_id == 949)
            )
            state = session.get(UserMedia, heat.id)
            assert state.status == TrackingStatus.WATCHED
            assert state.personal_rating == 9
            assert state.personal_note == "Harika film"
    finally:
        service.close()
        engine.dispose()


def test_letterboxd_watchlist_csv_marks_planned(tmp_path):
    path = tmp_path / "watchlist.csv"
    path.write_text(
        "tmdb_id,Name,Year\n603,The Matrix,1999\n",
        encoding="utf-8",
    )
    parsed = letterboxd_to_export(path)
    assert parsed.document.tracking[0].status == "PLANNED"
    assert parsed.document.media[0].tmdb_id == 603
