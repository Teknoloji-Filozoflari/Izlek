"""Central, UI-independent TMDb HTTP client."""

import math
import time
from collections.abc import Callable, Mapping
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from izlek.tmdb import endpoints
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

_Response = TypeVar("_Response", bound=BaseModel)
_TIMEOUT = 8.0
_MAX_RETRIES = 1
_MAX_RETRY_DELAY = 2.0


class TMDbError(Exception):
    """A safe error that never includes request headers or response content."""


class AuthenticationError(TMDbError):
    """The Bearer token is missing, invalid, or unauthorized."""


class RateLimitError(TMDbError):
    """TMDb still limits requests after bounded retries."""


class NotFoundError(TMDbError):
    """The requested TMDb object does not exist."""


class NetworkError(TMDbError):
    """The request could not reach TMDb or timed out."""


class TMDbServerError(TMDbError):
    """TMDb returned a server error."""


class InvalidResponseError(TMDbError):
    """TMDb returned JSON that does not match the expected schema."""


class TokenValidationError(TMDbError):
    """A safe user-facing onboarding validation failure."""


class TmdbClient:
    """Send bounded, authenticated requests and parse typed TMDb responses."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        token: str | None = None,
    ) -> None:
        self._client = client
        self._sleep = sleeper
        self._token = token

    def _get(
        self,
        path: str,
        token: str,
        params: Mapping[str, str | int] | None = None,
    ) -> httpx.Response:
        if not token.strip():
            raise AuthenticationError("TMDb tokenı gerekli.")
        client = self._client or httpx.Client(follow_redirects=False)
        try:
            for attempt in range(_MAX_RETRIES + 1):
                try:
                    response = client.get(
                        endpoints.BASE_URL + path,
                        params=params,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "accept": "application/json",
                        },
                        timeout=_TIMEOUT,
                    )
                except httpx.TimeoutException:
                    raise NetworkError(
                        "TMDb bağlantısı zaman aşımına uğradı."
                    ) from None
                except httpx.RequestError:
                    raise NetworkError(
                        "TMDb'ye bağlanılamadı. İnternetinizi kontrol edin."
                    ) from None
                if response.status_code != 429 or attempt == _MAX_RETRIES:
                    break
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = 0.5
                if not math.isfinite(delay):
                    delay = 0.5
                self._sleep(min(max(delay, 0.0), _MAX_RETRY_DELAY))

            if response.status_code in (401, 403):
                raise AuthenticationError("TMDb tokenı geçersiz veya yetkisiz.")
            if response.status_code == 429:
                raise RateLimitError(
                    "TMDb istek sınırına ulaşıldı. Biraz sonra deneyin."
                )
            if response.status_code == 404:
                raise NotFoundError("TMDb kaydı bulunamadı.")
            if response.status_code >= 500:
                raise TMDbServerError("TMDb şu anda yanıt veremiyor. Sonra deneyin.")
            if response.status_code != 200:
                raise TMDbError("TMDb isteği tamamlanamadı.")
            return response
        finally:
            if self._client is None:
                client.close()

    def _parse(self, response: httpx.Response, model: type[_Response]) -> _Response:
        try:
            return model.model_validate(response.json())
        except (ValueError, UnicodeError, ValidationError):
            raise InvalidResponseError("TMDb yanıtı okunamadı.") from None

    def _request(
        self,
        path: str,
        model: type[_Response],
        params: Mapping[str, str | int] | None = None,
    ) -> _Response:
        return self._parse(self._get(path, self._token or "", params), model)

    def validate_token(self, token: str) -> None:
        """Confirm an onboarding token without exposing low-level errors to QML."""
        if not token.strip():
            raise TokenValidationError("TMDb tokenı girin.")
        try:
            response = self._get(endpoints.AUTHENTICATION, token)
            if response.json().get("success") is not True:
                raise TokenValidationError("TMDb tokenı doğrulanamadı.")
        except (AttributeError, ValueError, UnicodeError):
            raise TokenValidationError("TMDb yanıtı okunamadı.") from None
        except TMDbError as exc:
            if isinstance(exc, TokenValidationError):
                raise
            raise TokenValidationError(str(exc)) from None

    def configuration(self) -> Configuration:
        """Fetch image URL and size configuration."""
        return self._request(endpoints.CONFIGURATION, Configuration)

    def search_movie(
        self, query: str, *, page: int = 1, language: str = "tr-TR"
    ) -> MovieSearchResults:
        """Search movies by title."""
        return self._request(
            endpoints.SEARCH_MOVIE,
            MovieSearchResults,
            {"query": query, "page": page, "language": language},
        )

    def search_tv(
        self, query: str, *, page: int = 1, language: str = "tr-TR"
    ) -> TvSearchResults:
        """Search television shows by title."""
        return self._request(
            endpoints.SEARCH_TV,
            TvSearchResults,
            {"query": query, "page": page, "language": language},
        )

    def discover_movie(
        self,
        *,
        page: int = 1,
        year: int | None = None,
        genre_id: int | None = None,
        country: str = "",
        min_score: float = 0.0,
        max_score: float = 10.0,
        min_vote_count: int = 100,
        language: str = "tr-TR",
    ) -> MovieSearchResults:
        """Discover movies ranked by score while excluding thinly voted titles."""
        return self._request(
            endpoints.DISCOVER_MOVIE,
            MovieSearchResults,
            self._discover_params(
                page, year, genre_id, country, min_score, max_score,
                min_vote_count, language, "primary_release_year"
            ),
        )

    def discover_tv(
        self,
        *,
        page: int = 1,
        year: int | None = None,
        genre_id: int | None = None,
        country: str = "",
        min_score: float = 0.0,
        max_score: float = 10.0,
        min_vote_count: int = 100,
        language: str = "tr-TR",
    ) -> TvSearchResults:
        """Discover TV series using the same score-quality guardrail."""
        return self._request(
            endpoints.DISCOVER_TV,
            TvSearchResults,
            self._discover_params(
                page, year, genre_id, country, min_score, max_score,
                min_vote_count, language, "first_air_date_year"
            ),
        )

    @staticmethod
    def _discover_params(
        page: int,
        year: int | None,
        genre_id: int | None,
        country: str,
        min_score: float,
        max_score: float,
        min_vote_count: int,
        language: str,
        year_key: str,
    ) -> dict[str, str | int]:
        """Build only supported Discover filters, with stable score ordering."""
        params: dict[str, str | int] = {
            "page": max(1, min(page, 500)),
            "language": language,
            "sort_by": "vote_average.desc",
            "vote_count.gte": max(0, min_vote_count),
            "vote_average.gte": f"{max(0.0, min(min_score, 10.0)):.1f}",
            "vote_average.lte": f"{max(0.0, min(max_score, 10.0)):.1f}",
        }
        if year is not None:
            params[year_key] = year
        if genre_id is not None:
            params["with_genres"] = genre_id
        if country:
            params["with_origin_country"] = country.upper()
        return params

    def movie(self, id: int, *, language: str = "tr-TR") -> MovieDetail:
        """Fetch a movie's metadata."""
        return self._request(
            endpoints.MOVIE.format(id=id), MovieDetail, {"language": language}
        )

    def movie_credits(self, id: int, *, language: str = "tr-TR") -> MovieCredits:
        """Fetch cast and crew for a movie."""
        return self._request(
            endpoints.MOVIE_CREDITS.format(id=id), MovieCredits, {"language": language}
        )

    def movie_videos(self, id: int, *, language: str = "tr-TR") -> MovieVideos:
        """Fetch trailers and other videos for a movie."""
        return self._request(
            endpoints.MOVIE_VIDEOS.format(id=id), MovieVideos, {"language": language}
        )

    def movie_similar(self, id: int, *, language: str = "tr-TR") -> MovieSearchResults:
        """Fetch similar movies."""
        return self._request(
            endpoints.MOVIE_SIMILAR.format(id=id),
            MovieSearchResults,
            {"language": language},
        )

    def movie_recommendations(
        self, id: int, *, language: str = "tr-TR"
    ) -> MovieSearchResults:
        """Fetch recommended movies."""
        return self._request(
            endpoints.MOVIE_RECOMMENDATIONS.format(id=id),
            MovieSearchResults,
            {"language": language},
        )

    def movie_watch_providers(self, id: int) -> MovieWatchProviders:
        """Fetch regional streaming, rental, and purchase options."""
        return self._request(
            endpoints.MOVIE_WATCH_PROVIDERS.format(id=id), MovieWatchProviders
        )

    def tv(self, id: int, *, language: str = "tr-TR") -> TvDetail:
        """Fetch a show's metadata and season summaries."""
        return self._request(
            endpoints.TV.format(id=id), TvDetail, {"language": language}
        )

    def tv_season(
        self, id: int, season_number: int, *, language: str = "tr-TR"
    ) -> SeasonDetail:
        """Fetch a season and its episodes."""
        return self._request(
            endpoints.TV_SEASON.format(id=id, season_number=season_number),
            SeasonDetail,
            {"language": language},
        )

    def tv_credits(self, id: int, *, language: str = "tr-TR") -> MovieCredits:
        return self._request(endpoints.TV_CREDITS.format(id=id), MovieCredits,
                             {"language": language})

    def tv_videos(self, id: int, *, language: str = "tr-TR") -> MovieVideos:
        return self._request(endpoints.TV_VIDEOS.format(id=id), MovieVideos,
                             {"language": language})

    def tv_similar(self, id: int, *, language: str = "tr-TR") -> TvSearchResults:
        return self._request(endpoints.TV_SIMILAR.format(id=id), TvSearchResults,
                             {"language": language})

    def tv_recommendations(
        self, id: int, *, language: str = "tr-TR"
    ) -> TvSearchResults:
        return self._request(endpoints.TV_RECOMMENDATIONS.format(id=id),
                             TvSearchResults, {"language": language})

    def tv_watch_providers(self, id: int) -> MovieWatchProviders:
        return self._request(endpoints.TV_WATCH_PROVIDERS.format(id=id),
                             MovieWatchProviders)
