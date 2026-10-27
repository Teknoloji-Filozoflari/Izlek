"""DiscoverService owns TMDb Discover filters and suppression flags."""

from izlek.services.discover import MIN_VOTE_COUNT, DiscoverService
from izlek.services.personal_media import PersonalMediaService
from izlek.tmdb.models import MovieSearchResults, TvSearchResults


class _Client:
    def __init__(self):
        self.calls = []

    def discover_movie(self, **filters):
        self.calls.append(("movie", filters))
        return MovieSearchResults.model_validate(
            {
                "page": filters["page"],
                "total_pages": 3,
                "total_results": 1,
                "results": [
                    {
                        "id": 10,
                        "title": "Hidden",
                        "original_title": "Movie Original",
                        "release_date": "2024-01-01",
                        "vote_average": 8.4,
                        "poster_path": "/p.jpg",
                    }
                ],
            }
        )

    def discover_tv(self, **filters):
        self.calls.append(("tv", filters))
        return TvSearchResults.model_validate(
            {
                "page": filters["page"],
                "total_pages": 1,
                "total_results": 1,
                "results": [
                    {
                        "id": 20,
                        "name": "Show",
                        "original_name": "Show Original",
                        "first_air_date": "2021-01-01",
                        "vote_average": 7.2,
                    }
                ],
            }
        )


def test_discover_service_converts_score_filters_and_marks_dismissed(
    initialized_factory,
):
    preferences = PersonalMediaService(initialized_factory)
    preferences.dismiss(
        {"id": 10, "mediaType": "movie", "title": "Hidden", "posterPath": ""}, True
    )
    client = _Client()
    service = DiscoverService(client, preferences)

    page = service.fetch_page(
        "movie",
        page=2,
        year=2024,
        genre_id=18,
        country="TR",
        min_score=75,
        max_score=90,
    )

    assert client.calls[-1] == (
        "movie",
        {
            "page": 2,
            "year": 2024,
            "genre_id": 18,
            "country": "TR",
            "min_score": 7.5,
            "max_score": 9.0,
            "min_vote_count": MIN_VOTE_COUNT,
        },
    )
    assert page.page == 2
    assert page.total_pages == 3
    assert page.items == [
        {
            "id": 10,
            "mediaType": "movie",
            "title": "Movie Original",
            "year": "2024",
            "releaseDate": "2024-01-01",
            "posterPath": "/p.jpg",
            "progressText": "TMDb 8.4",
            "score": 8.4,
            "dismissed": True,
        }
    ]
    preferences.close()


def test_discover_service_tv_page_without_hidden_ids(initialized_factory):
    service = DiscoverService(_Client(), PersonalMediaService(initialized_factory))
    page = service.fetch_page("tv", page=1)
    assert page.items[0]["title"] == "Show Original"
    assert page.items[0]["dismissed"] is False
    service._preferences.close()
