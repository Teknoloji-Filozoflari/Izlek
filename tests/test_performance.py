"""Large local dataset budgets for Phase 24 performance regressions."""

from collections.abc import Iterator
from concurrent.futures import Future
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from time import perf_counter

from sqlalchemy import Engine, event

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
from izlek.services.continue_watching import ContinueWatchingService
from izlek.services.custom_lists import CustomListsService
from izlek.services.movie_detail import MovieDetailService
from izlek.services.movie_library import MovieLibraryService
from izlek.services.tv_detail import TvDetailService
from izlek.services.tv_library import TvLibraryService
from izlek.ui.controllers.library_controller import LibraryController


@contextmanager
def query_count(engine: Engine) -> Iterator[list[int]]:
    count = [0]

    def before_cursor_execute(*_args) -> None:
        count[0] += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield count
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


class OfflineTmdb:
    """A guard: local performance scenarios must never request TMDb."""

    def __getattr__(self, name):
        raise AssertionError(f"Beklenmeyen TMDb çağrısı: {name}")


def seed_large_library(factory) -> None:
    movies = [
        MediaItem(
            tmdb_id=10_000 + index,
            media_type=MediaType.MOVIE,
            original_title=f"Film {index:03d}",
            release_date=date(2020, 1, 1),
            poster_path=f"/movie-{index}.jpg",
            metadata_json={
                "detail": {
                    "id": 10_000 + index,
                    "title": f"Film {index:03d}",
                    "original_title": f"Film {index:03d}",
                    "vote_average": 7.0,
                }
            },
        )
        for index in range(500)
    ]
    shows = [
        MediaItem(
            tmdb_id=20_000 + index,
            media_type=MediaType.TV,
            original_title=f"Dizi {index:03d}",
            first_air_date=date(2020, 1, 1),
            poster_path=f"/show-{index}.jpg",
            metadata_json={
                "detail": {
                    "id": 20_000 + index,
                    "name": f"Dizi {index:03d}",
                    "original_name": f"Dizi {index:03d}",
                    "vote_average": 8.0,
                    "seasons": [
                        {
                            "id": 30_000 + index,
                            "season_number": 1,
                            "name": "Sezon 1",
                            "episode_count": 50,
                        }
                    ],
                }
            },
        )
        for index in range(200)
    ]
    with factory.begin() as session:
        session.add_all(movies + shows)
        session.flush()
        media = movies + shows
        session.add_all(
            UserMedia(
                media_id=item.id,
                status=(
                    TrackingStatus.WATCHING
                    if item.media_type == MediaType.TV
                    else TrackingStatus.PLANNED
                ),
                favorite=item.id % 10 == 0,
            )
            for item in media
        )
        seasons = [
            Season(media_id=show.id, season_number=1, name="Sezon 1")
            for show in shows
        ]
        session.add_all(seasons)
        session.flush()
        episodes = [
            Episode(
                season_id=season.id,
                episode_number=number,
                name=f"Bölüm {number}",
                air_date=date(2020, 1, 1),
            )
            for season in seasons
            for number in range(1, 51)
        ]
        session.add_all(episodes)
        session.flush()
        session.add_all(
            EpisodeProgress(episode_id=episode.id, watched=True)
            for episode in episodes[::5]
        )
        lists = [
            CustomList(name=f"Liste {index}", sort_order=index)
            for index in range(20)
        ]
        session.add_all(lists)
        session.flush()
        session.add_all(
            CustomListItem(list_id=item.id, media_id=movies[0].id, sort_order=0)
            for item in lists
        )


def test_large_library_query_budgets_and_runtime(tmp_path):
    engine = initialize_database(tmp_path / "large.sqlite3")
    factory = create_session_factory(engine)
    seed_large_library(factory)
    started = perf_counter()

    with query_count(engine) as count:
        movies = MovieLibraryService(factory).snapshot(TrackingStatus.PLANNED)
    assert len(movies.items) == 500
    assert count[0] == 1

    with query_count(engine) as count:
        shows = TvLibraryService(factory).snapshot(TrackingStatus.WATCHING)
    assert len(shows.items) == 200
    assert count[0] == 2

    with query_count(engine) as count:
        continuing = ContinueWatchingService(factory).list_next()
    assert len(continuing) == 200
    assert count[0] == 1

    with query_count(engine) as count:
        season = TvDetailService(OfflineTmdb(), factory).cached_season(20_000, 1)
    assert season is not None and len(season) == 50
    assert count[0] == 3

    with query_count(engine) as count:
        lists = CustomListsService(factory).snapshot()
    assert len(lists["lists"]) == 20
    assert count[0] == 3

    with query_count(engine) as count:
        movie_detail = MovieDetailService(OfflineTmdb(), factory).cached(10_000)
    assert movie_detail is not None and len(movie_detail["lists"]) == 20
    assert count[0] == 4

    with query_count(engine) as count:
        tv_detail = TvDetailService(OfflineTmdb(), factory).cached(20_000)
    assert tv_detail is not None and tv_detail["watchedEpisodeCount"] == 10
    assert count[0] == 5

    assert perf_counter() - started < 5.0
    engine.dispose()


class StubService:
    def close(self) -> None:
        pass


class CountingImages:
    def __init__(self, result: Path) -> None:
        self.result = result
        self.requests: list[str] = []

    def poster(self, path: str) -> Future[Path]:
        self.requests.append(path)
        future: Future[Path] = Future()
        future.set_result(self.result)
        return future


def test_large_grid_requests_only_instantiated_thumbnails(tmp_path):
    images = CountingImages(tmp_path / "placeholder.svg")
    controller = LibraryController(service=StubService(), images=images)
    controller._generation = 1
    items = [
        {
            "tmdb_id": index,
            "poster_path": f"/{index}.jpg",
            "title": f"Film {index}",
        }
        for index in range(500)
    ]
    controller._apply_loaded(1, items, [], {"total": 500}, "")
    assert images.requests == []

    for item in items[:12]:
        controller.requestPoster(item["tmdb_id"])
    assert len(images.requests) == 12

    controller.requestPoster(items[0]["tmdb_id"])
    assert len(images.requests) == 12
    controller.close()
