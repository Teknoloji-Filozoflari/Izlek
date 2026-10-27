"""Local-taste For You strip uses TMDb neighbors without external ML."""

from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.services.discover import DiscoverService
from izlek.services.personal_media import PersonalMediaService
from izlek.services.recommendations import ForYouService
from izlek.tmdb.models import MovieSearchResults


class _Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int | None]] = []

    def movie_recommendations(self, movie_id: int, **_kwargs):
        self.calls.append(("rec", movie_id))
        return MovieSearchResults.model_validate(
            {
                "page": 1,
                "total_pages": 1,
                "total_results": 1,
                "results": [
                    {
                        "id": 900,
                        "title": "Neighbor",
                        "original_title": "Neighbor",
                        "release_date": "2020-01-01",
                        "vote_average": 7.5,
                    }
                ],
            }
        )

    def movie_similar(self, movie_id: int, **_kwargs):
        self.calls.append(("similar", movie_id))
        return MovieSearchResults.model_validate(
            {
                "page": 1,
                "total_pages": 1,
                "total_results": 1,
                "results": [
                    {
                        "id": 901,
                        "title": "Similar",
                        "original_title": "Similar",
                        "release_date": "2019-01-01",
                        "vote_average": 7.1,
                    }
                ],
            }
        )

    def discover_movie(self, **filters):
        self.calls.append(("discover", filters.get("genre_id")))
        return MovieSearchResults.model_validate(
            {
                "page": 1,
                "total_pages": 1,
                "total_results": 1,
                "results": [
                    {
                        "id": 902,
                        "title": "Genre Hit",
                        "original_title": "Genre Hit",
                        "release_date": "2021-01-01",
                        "vote_average": 8.0,
                    }
                ],
            }
        )


def _seed_favorite(factory) -> None:
    with factory.begin() as session:
        media = MediaRepository(session).upsert(
            42,
            MediaType.MOVIE,
            "Seed Film",
            metadata_json={
                "detail": {
                    "id": 42,
                    "title": "Seed Film",
                    "original_title": "Seed Film",
                    "genres": [{"id": 28, "name": "Action"}],
                }
            },
        )
        users = UserMediaRepository(session)
        users.set_status(media.id, TrackingStatus.WATCHED)
        users.set_favorite(media.id, True)
        users.set_personal(media.id, 9, "great")


def test_for_you_uses_local_taste_and_tmdb_neighbors(initialized_factory):
    _seed_favorite(initialized_factory)
    service = ForYouService(_Client(), initialized_factory)
    items = service.fetch("movie")
    ids = {item["id"] for item in items}
    assert 900 in ids
    assert 901 in ids
    assert 902 in ids
    assert 42 not in ids


def test_discover_service_for_you_empty_without_taste(initialized_factory):
    client = _Client()
    service = DiscoverService(
        client, preferences=PersonalMediaService(initialized_factory)
    )
    assert service.for_you("movie") == []
    assert client.calls == []


def test_for_you_skips_dismissed_seeds(initialized_factory):
    with initialized_factory.begin() as session:
        media = MediaRepository(session).upsert(
            7,
            MediaType.MOVIE,
            "Hidden",
            metadata_json={"detail": {"id": 7, "genres": [{"id": 18, "name": "Drama"}]}},
        )
        users = UserMediaRepository(session)
        users.set_favorite(media.id, True)
        users.set_dismissed(media.id, True)
    service = ForYouService(_Client(), initialized_factory)
    assert service.fetch("movie") == []
