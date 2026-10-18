"""Combined offline filters over cached library metadata."""

from dataclasses import dataclass
from typing import TypeVar

from izlek.db.models import MediaItem, TrackingStatus

Item = TypeVar("Item")


def cached_genres(media: MediaItem) -> tuple[str, ...]:
    detail = (media.metadata_json or {}).get("detail") or {}
    genres = detail.get("genres", []) if isinstance(detail, dict) else []
    return (
        tuple(
            sorted(
                {
                    str(row["name"])
                    for row in genres
                    if isinstance(row, dict) and row.get("name")
                }
            )
        )
        if isinstance(genres, list)
        else ()
    )


def cached_runtime(media: MediaItem) -> int | None:
    if media.runtime and media.runtime > 0:
        return media.runtime
    detail = (media.metadata_json or {}).get("detail") or {}
    values = detail.get("episode_run_time", []) if isinstance(detail, dict) else []
    return (
        max(
            (value for value in values if type(value) is int and value > 0),
            default=None,
        )
        if isinstance(values, list)
        else None
    )


@dataclass(frozen=True)
class LibraryFilters:
    status: str = ""
    genre: str = ""
    year_from: int = 0
    year_to: int = 0
    max_runtime: int = 0
    min_score: float = 0

    @classmethod
    def parse(cls, values: dict) -> "LibraryFilters":
        filters = cls(
            status=str(values.get("status") or ""),
            genre=str(values.get("genre") or ""),
            year_from=int(values.get("year_from") or 0),
            year_to=int(values.get("year_to") or 0),
            max_runtime=int(values.get("max_runtime") or 0),
            min_score=float(values.get("min_score") or 0),
        )
        if (
            filters.status
            and filters.status not in TrackingStatus._value2member_map_
            or any(
                year and not 1888 <= year <= 2100
                for year in (filters.year_from, filters.year_to)
            )
            or filters.year_from
            and filters.year_to
            and filters.year_from > filters.year_to
            or not 0 <= filters.max_runtime <= 1440
            or not 0 <= filters.min_score <= 10
        ):
            raise ValueError("Filtre aralıklarını kontrol edin.")
        return filters

    @property
    def active(self) -> bool:
        return self != LibraryFilters()

    def apply(self, items: list[Item]) -> list[Item]:
        result = []
        for item in items:
            year = int(item.year) if item.year else 0
            if (
                self.status
                and item.status != self.status
                or self.genre
                and self.genre not in item.genres
                or self.year_from
                and (not year or year < self.year_from)
                or self.year_to
                and (not year or year > self.year_to)
                or self.max_runtime
                and (not item.runtime or item.runtime > self.max_runtime)
                or self.min_score
                and (item.score is None or item.score < self.min_score)
            ):
                continue
            result.append(item)
        return result
