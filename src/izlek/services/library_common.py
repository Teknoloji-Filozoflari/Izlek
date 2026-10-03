"""Shared local library ordering and status counts."""

from datetime import datetime
from typing import Protocol, TypeVar

from izlek.db.models import MediaItem, TrackingStatus

SORT_RECENT = "recent"
SORT_TITLE = "title"
SORT_YEAR = "year"
SORT_SCORE = "score"
SORT_OPTIONS = frozenset({SORT_RECENT, SORT_TITLE, SORT_YEAR, SORT_SCORE})


class SortableItem(Protocol):
    tmdb_id: int
    title: str
    year: str
    score: float | None
    status: str
    added_at: datetime


ItemT = TypeVar("ItemT", bound=SortableItem)


def metadata_score(media: MediaItem) -> float | None:
    """Read the cached TMDb rating when the detail payload contains one."""
    detail = (media.metadata_json or {}).get("detail") or {}
    raw = detail.get("vote_average") if isinstance(detail, dict) else None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    return float(raw)


def sort_items(items: list[ItemT], sort_by: str) -> list[ItemT]:
    """Sort library entries with missing year and score values last."""
    if sort_by == SORT_TITLE:
        return sorted(items, key=lambda item: (item.title.casefold(), item.tmdb_id))
    if sort_by == SORT_YEAR:
        return sorted(
            items,
            key=lambda item: (
                -(int(item.year) if item.year else -1),
                item.title.casefold(),
                item.tmdb_id,
            ),
        )
    if sort_by == SORT_SCORE:
        return sorted(
            items,
            key=lambda item: (
                -(item.score if item.score is not None else -1),
                item.title.casefold(),
                item.tmdb_id,
            ),
        )
    return sorted(items, key=lambda item: (-item.added_at.timestamp(), -item.tmdb_id))


def status_counts(items: list[SortableItem]) -> dict[str, int]:
    """Count tracked items; favorite-only entries remain outside the total."""
    tracked = [item for item in items if item.status]
    return {
        "total": len(tracked),
        "planned": sum(item.status == TrackingStatus.PLANNED for item in tracked),
        "watching": sum(item.status == TrackingStatus.WATCHING for item in tracked),
        "watched": sum(item.status == TrackingStatus.WATCHED for item in tracked),
    }
