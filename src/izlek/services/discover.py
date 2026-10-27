"""TMDb Discover queries and recommendation-visibility filtering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from izlek.services.personal_media import PersonalMediaService
from izlek.tmdb.client import TmdbClient
from izlek.tmdb.models import MovieSummary, TvSummary

MIN_VOTE_COUNT = 100


@dataclass(frozen=True)
class DiscoverPage:
    """One Discover response ready for the controller/UI layer."""

    page: int
    total_pages: int
    items: list[dict[str, Any]]


class DiscoverService:
    """Keep Discover business rules out of the Qt controller."""

    def __init__(
        self,
        client: TmdbClient,
        preferences: PersonalMediaService | None = None,
    ) -> None:
        self._client = client
        self._preferences = preferences or PersonalMediaService()

    def fetch_page(
        self,
        kind: str,
        *,
        page: int = 1,
        year: int = 0,
        genre_id: int = 0,
        country: str = "",
        min_score: int = 0,
        max_score: int = 100,
        min_vote_count: int = MIN_VOTE_COUNT,
    ) -> DiscoverPage:
        """Load one Discover page and mark locally suppressed titles."""
        if kind not in {"movie", "tv"}:
            raise ValueError("Geçersiz medya türü")
        filters = {
            "page": page,
            "year": year or None,
            "genre_id": genre_id or None,
            "country": country,
            "min_score": min_score / 10,
            "max_score": max_score / 10,
            "min_vote_count": min_vote_count,
        }
        result = (
            self._client.discover_movie(**filters)
            if kind == "movie"
            else self._client.discover_tv(**filters)
        )
        hidden = self._preferences.suppressed_ids(kind)
        items = [
            {**self.summary_dict(item, kind), "dismissed": item.id in hidden}
            for item in result.results
        ]
        return DiscoverPage(
            page=result.page, total_pages=result.total_pages, items=items
        )

    @staticmethod
    def summary_dict(item: MovieSummary | TvSummary, kind: str) -> dict[str, Any]:
        """Convert a TMDb summary into the Discover card payload (sans poster URL)."""
        title = item.original_title if kind == "movie" else item.original_name
        date = item.release_date if kind == "movie" else item.first_air_date
        return {
            "id": item.id,
            "mediaType": kind,
            "title": title,
            "year": date[:4] if date else "",
            "releaseDate": date or "",
            "posterPath": item.poster_path or "",
            "progressText": f"TMDb {item.vote_average:.1f}",
            "score": item.vote_average,
        }
