"""Local-taste recommendation strip backed by TMDb (no external ML)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from izlek.db.models import MediaType, TrackingStatus, UserMedia
from izlek.repositories.local import MediaRepository
from izlek.tmdb.client import NetworkError, TmdbClient, TMDbError
from izlek.tmdb.models import MovieSummary, TvSummary

_SEED_LIMIT = 5
_RESULT_LIMIT = 12
_MIN_RATING = 7


def _summary_dict(item: MovieSummary | TvSummary, kind: str) -> dict[str, Any]:
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


def _genre_ids(blob: dict[str, Any] | None) -> list[int]:
    detail = (blob or {}).get("detail") or {}
    genres = detail.get("genres") or []
    ids: list[int] = []
    for genre in genres:
        if isinstance(genre, dict) and genre.get("id") is not None:
            try:
                ids.append(int(genre["id"]))
            except (TypeError, ValueError):
                continue
    return ids


def _seed_weight(user: UserMedia) -> int:
    weight = 0
    if user.favorite:
        weight += 3
    if user.personal_rating and user.personal_rating >= _MIN_RATING:
        weight += int(user.personal_rating)
    if user.status == TrackingStatus.WATCHED:
        weight += 1
    elif user.status is not None:
        weight += 1
    return weight


class ForYouService:
    """Build a short strip from local favorites/ratings/genres + TMDb neighbors."""

    def __init__(
        self,
        client: TmdbClient,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._client = client
        self._factory = session_factory

    def taste_seeds(self, kind: str) -> tuple[list[dict[str, Any]], list[int]]:
        """Return ranked seed titles and top genre ids for one media kind."""
        media_type = MediaType(kind.upper())
        with self._factory() as session:
            rows = MediaRepository(session).list_all_with_tracking()
            seeds: list[tuple[int, dict[str, Any]]] = []
            genre_weights: Counter[int] = Counter()
            for media, user in rows:
                if media.media_type != media_type or user is None:
                    continue
                if user.dismissed:
                    continue
                weight = _seed_weight(user)
                if weight <= 0:
                    continue
                for genre_id in _genre_ids(media.metadata_json):
                    genre_weights[genre_id] += weight
                seeds.append(
                    (
                        weight,
                        {
                            "id": media.tmdb_id,
                            "title": media.original_title,
                            "weight": weight,
                        },
                    )
                )
            seeds.sort(key=lambda item: (-item[0], item[1]["id"]))
            top_genres = [genre for genre, _ in genre_weights.most_common(3)]
            return [entry for _, entry in seeds[:_SEED_LIMIT]], top_genres

    def fetch(self, kind: str) -> list[dict[str, Any]]:
        """Assemble recommendations/similar/discover rows, excluding local noise."""
        if kind not in {"movie", "tv"}:
            raise ValueError("Geçersiz medya türü")
        seeds, top_genres = self.taste_seeds(kind)
        if not seeds and not top_genres:
            return []
        with self._factory() as session:
            excluded = MediaRepository(session).recommendation_excluded_ids(
                MediaType(kind.upper())
            )
            library = MediaRepository(session).excluded_tmdb_ids(
                MediaType(kind.upper())
            )
        blocked = set(excluded) | set(library) | {seed["id"] for seed in seeds}
        scored: dict[int, tuple[float, dict[str, Any]]] = {}

        def consider(item: MovieSummary | TvSummary, bonus: float) -> None:
            if item.id in blocked:
                return
            existing = scored.get(item.id)
            if existing is not None and existing[0] >= bonus:
                return
            payload = _summary_dict(item, kind)
            payload["reason"] = "for_you"
            scored[item.id] = (bonus, payload)

        for seed in seeds:
            seed_id = int(seed["id"])
            seed_bonus = float(seed["weight"])
            try:
                if kind == "movie":
                    recs = self._client.movie_recommendations(seed_id)
                    similar = self._client.movie_similar(seed_id)
                else:
                    recs = self._client.tv_recommendations(seed_id)
                    similar = self._client.tv_similar(seed_id)
            except (TMDbError, NetworkError, OSError, ValueError):
                continue
            for entry in recs.results[:8]:
                consider(entry, seed_bonus + 2.0)
            for entry in similar.results[:6]:
                consider(entry, seed_bonus + 1.0)

        for genre_id in top_genres[:2]:
            try:
                page = (
                    self._client.discover_movie(
                        page=1, genre_id=genre_id, min_vote_count=100
                    )
                    if kind == "movie"
                    else self._client.discover_tv(
                        page=1, genre_id=genre_id, min_vote_count=100
                    )
                )
            except (TMDbError, NetworkError, OSError, ValueError):
                continue
            for entry in page.results[:8]:
                consider(entry, 1.5)

        ranked = sorted(scored.values(), key=lambda pair: (-pair[0], -pair[1]["score"]))
        return [payload for _, payload in ranked[:_RESULT_LIMIT]]
