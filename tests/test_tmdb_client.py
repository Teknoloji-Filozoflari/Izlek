"""TMDb API tests use local HTTP responses only."""

import httpx
import pytest

from izlek.tmdb.client import (
    AuthenticationError,
    InvalidResponseError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    TmdbClient,
    TMDbServerError,
)
from izlek.tmdb.models import (
    Configuration,
    MovieCredits,
    MovieDetail,
    MovieSearchResults,
    MovieVideos,
    MovieWatchProviders,
    SeasonDetail,
    TvDetail,
    TvSearchResults,
)

TOKEN = "secret-for-test"


def make_client(respond, *, sleeper=lambda delay: None):
    http_client = httpx.Client(transport=httpx.MockTransport(respond))
    return http_client, TmdbClient(http_client, sleeper=sleeper, token=TOKEN)


@pytest.mark.parametrize(
    ("method", "args", "path", "payload", "expected"),
    [
        (
            "configuration",
            (),
            "/configuration",
            {
                "images": {
                    "secure_base_url": "https://images.example/",
                    "poster_sizes": ["w500"],
                    "backdrop_sizes": ["w780"],
                }
            },
            Configuration,
        ),
        (
            "search_movie",
            ("Arrival",),
            "/search/movie",
            {
                "page": 1,
                "total_pages": 1,
                "total_results": 1,
                "results": [{"id": 1, "title": "Arrival", "original_title": "Arrival"}],
            },
            MovieSearchResults,
        ),
        (
            "search_tv",
            ("Dark",),
            "/search/tv",
            {
                "page": 1,
                "total_pages": 1,
                "total_results": 1,
                "results": [{"id": 2, "name": "Dark", "original_name": "Dark"}],
            },
            TvSearchResults,
        ),
        (
            "movie",
            (1,),
            "/movie/1",
            {"id": 1, "title": "Arrival", "original_title": "Arrival", "runtime": 116},
            MovieDetail,
        ),
        (
            "tv",
            (2,),
            "/tv/2",
            {
                "id": 2,
                "name": "Dark",
                "original_name": "Dark",
                "seasons": [{"id": 20, "season_number": 1, "name": "Season 1"}],
            },
            TvDetail,
        ),
        (
            "tv_season",
            (2, 1),
            "/tv/2/season/1",
            {
                "id": 20,
                "season_number": 1,
                "name": "Season 1",
                "episodes": [{"id": 201, "episode_number": 1, "name": "Pilot"}],
            },
            SeasonDetail,
        ),
    ],
)
def test_endpoints_use_bearer_and_return_typed_models(
    method, args, path, payload, expected
):
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, json=payload)

    http_client, client = make_client(respond)
    with http_client:
        result = getattr(client, method)(*args)

    assert isinstance(result, expected)
    assert seen[0].url.path == "/3" + path
    assert seen[0].headers["Authorization"] == f"Bearer {TOKEN}"
    if method.startswith("search_"):
        assert seen[0].url.params["query"] == args[0]
        assert seen[0].url.params["language"] == "tr-TR"
    if isinstance(result, MovieSearchResults):
        assert result.results[0].original_title == "Arrival"
    if isinstance(result, SeasonDetail):
        assert result.episodes[0].episode_number == 1


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, NotFoundError),
        (429, RateLimitError),
        (500, TMDbServerError),
        (503, TMDbServerError),
    ],
)
def test_http_errors_are_safe(status, error):
    requests = []
    delays = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            status,
            headers={"Retry-After": "999"},
            json={"status_message": TOKEN},
        )

    http_client, client = make_client(respond, sleeper=delays.append)
    with http_client, pytest.raises(error) as caught:
        client.movie(1)
    assert TOKEN not in str(caught.value)
    assert len(requests) == (2 if status == 429 else 1)
    assert delays == ([2.0] if status == 429 else [])


@pytest.mark.parametrize("payload", [[], {"id": "wrong"}, {"id": 1}])
def test_malformed_schema_becomes_safe_domain_error(payload):
    http_client, client = make_client(lambda request: httpx.Response(200, json=payload))
    with http_client, pytest.raises(InvalidResponseError) as caught:
        client.movie(1)
    assert TOKEN not in str(caught.value)


def test_invalid_json_becomes_safe_domain_error():
    http_client, client = make_client(
        lambda request: httpx.Response(200, content=b"not-json")
    )
    with http_client, pytest.raises(InvalidResponseError):
        client.configuration()


@pytest.mark.parametrize(
    "failure", [httpx.ReadTimeout("secret"), httpx.ConnectError("secret")]
)
def test_network_failures_become_safe_domain_errors(failure):
    def fail(request):
        raise failure

    http_client, client = make_client(fail)
    with http_client, pytest.raises(NetworkError) as caught:
        client.search_tv("Dark")
    assert "secret" not in str(caught.value)
    assert caught.value.__cause__ is None


def test_rate_limit_retries_then_succeeds():
    requests = []
    delays = []

    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, headers={"Retry-After": "0.25"})
        return httpx.Response(
            200, json={"id": 1, "title": "Arrival", "original_title": "Arrival"}
        )

    http_client, client = make_client(respond, sleeper=delays.append)
    with http_client:
        assert client.movie(1).id == 1
    assert len(requests) == 2
    assert delays == [0.25]


def test_discover_uses_score_order_and_vote_threshold():
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "page": 2,
                "total_pages": 3,
                "total_results": 3,
                "results": [
                    {"id": 7, "title": "Original", "original_title": "Original"}
                ],
            },
        )

    http_client, client = make_client(respond)
    with http_client:
        result = client.discover_movie(
            page=2,
            year=2024,
            genre_id=18,
            country="tr",
            min_score=7.5,
            max_score=9.0,
        )

    assert result.page == 2
    assert seen[0].url.path == "/3/discover/movie"
    assert dict(seen[0].url.params) == {
        "page": "2",
        "language": "tr-TR",
        "sort_by": "vote_average.desc",
        "vote_count.gte": "100",
        "vote_average.gte": "7.5",
        "vote_average.lte": "9.0",
        "primary_release_year": "2024",
        "with_genres": "18",
        "with_origin_country": "TR",
    }


def test_missing_token_fails_before_network():
    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("network called"))
    )
    with http_client, pytest.raises(AuthenticationError):
        TmdbClient(http_client).configuration()


@pytest.mark.parametrize(
    ("method", "args", "path", "payload", "expected"),
    [
        ("movie_credits", (11,), "/movie/11/credits", {"id": 11}, MovieCredits),
        ("movie_videos", (11,), "/movie/11/videos", {"id": 11}, MovieVideos),
        (
            "movie_similar",
            (11,),
            "/movie/11/similar",
            {"page": 1, "results": [], "total_pages": 0, "total_results": 0},
            MovieSearchResults,
        ),
        (
            "movie_recommendations",
            (11,),
            "/movie/11/recommendations",
            {"page": 1, "results": [], "total_pages": 0, "total_results": 0},
            MovieSearchResults,
        ),
        (
            "movie_watch_providers",
            (11,),
            "/movie/11/watch/providers",
            {"id": 11, "results": {}},
            MovieWatchProviders,
        ),
        ("tv_credits", (22,), "/tv/22/credits", {"id": 22}, MovieCredits),
        ("tv_videos", (22,), "/tv/22/videos", {"id": 22}, MovieVideos),
        (
            "tv_similar",
            (22,),
            "/tv/22/similar",
            {"page": 1, "results": [], "total_pages": 0, "total_results": 0},
            TvSearchResults,
        ),
        (
            "tv_recommendations",
            (22,),
            "/tv/22/recommendations",
            {"page": 1, "results": [], "total_pages": 0, "total_results": 0},
            TvSearchResults,
        ),
        (
            "tv_watch_providers",
            (22,),
            "/tv/22/watch/providers",
            {"id": 22, "results": {}},
            MovieWatchProviders,
        ),
    ],
)
def test_detail_section_endpoints_are_mocked_and_typed(
    method, args, path, payload, expected
):
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, json=payload)

    http_client, client = make_client(respond)
    with http_client:
        result = getattr(client, method)(*args)

    assert isinstance(result, expected)
    assert seen[0].url.path == "/3" + path
    assert seen[0].headers["Authorization"] == f"Bearer {TOKEN}"
    if "watch/providers" not in path:
        assert seen[0].url.params["language"] == "tr-TR"


@pytest.mark.parametrize("retry_after", ["invalid", "nan", "-12"])
def test_rate_limit_retry_delay_is_bounded(retry_after):
    delays = []
    requests = []

    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, headers={"Retry-After": retry_after})
        return httpx.Response(
            200, json={"id": 1, "title": "Arrival", "original_title": "Arrival"}
        )

    http_client, client = make_client(respond, sleeper=delays.append)
    with http_client:
        assert client.movie(1).id == 1

    assert delays == ([0.0] if retry_after == "-12" else [0.5])
