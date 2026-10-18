"""Resolve people and select acting or directing credits by role."""

from izlek.tmdb.client import TmdbClient
from izlek.tmdb.models import MovieSummary, TvSummary


class DirectorSearchService:
    def __init__(self, client: TmdbClient) -> None:
        self._client = client

    def search(self, query: str, role: str = "director") -> list[dict]:
        """Prioritize the requested department without excluding other roles."""
        if role not in ("director", "actor"):
            raise ValueError("Geçersiz kişi rolü")
        people = self._client.search_person(query).results
        department = "Acting" if role == "actor" else "Directing"
        people = sorted(
            people, key=lambda person: person.known_for_department != department
        )
        return [{"id": person.id, "name": person.name} for person in people]

    def works(
        self, person_id: int, kind: str, role: str = "director"
    ) -> list[MovieSummary | TvSummary]:
        """Select cast or Director jobs, deduplicate and sort newest first."""
        if kind not in ("movie", "tv") or role not in ("director", "actor"):
            raise ValueError("Geçersiz medya türü")
        credits = (
            self._client.person_movie_credits(person_id)
            if kind == "movie"
            else self._client.person_tv_credits(person_id)
        )
        works = (
            credits.cast
            if role == "actor"
            else [item for item in credits.crew if item.job == "Director"]
        )
        unique = {item.id: item for item in works}
        return sorted(
            unique.values(),
            key=lambda item: (
                item.release_date or ""
                if kind == "movie"
                else item.first_air_date or "",
                item.id,
            ),
            reverse=True,
        )
