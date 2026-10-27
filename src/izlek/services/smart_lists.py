"""Built-in and tag-backed smart lists; membership is computed, never stored."""

from collections.abc import Callable
from dataclasses import dataclass

from izlek.db.models import MediaItem, TrackingStatus, UserMedia

SMART_ID_UNWATCHED_FAVORITES = -1
SMART_ID_FAVORITES = -2
SMART_ID_WATCHING = -3
SMART_ID_PLANNED = -4
SMART_ID_HIGHLY_RATED = -5
_TAG_LIST_BASE = -1000


@dataclass(frozen=True)
class SmartListDefinition:
    id: int
    key: str
    name: str
    description: str
    match: Callable[[MediaItem, UserMedia | None], bool]


def _unwatched_favorite(_media: MediaItem, user: UserMedia | None) -> bool:
    return bool(user and user.favorite and user.status != TrackingStatus.WATCHED)


def _favorite(_media: MediaItem, user: UserMedia | None) -> bool:
    return bool(user and user.favorite)


def _watching(_media: MediaItem, user: UserMedia | None) -> bool:
    return bool(user and user.status == TrackingStatus.WATCHING)


def _planned(_media: MediaItem, user: UserMedia | None) -> bool:
    return bool(user and user.status == TrackingStatus.PLANNED)


def _highly_rated(_media: MediaItem, user: UserMedia | None) -> bool:
    return bool(user and user.personal_rating is not None and user.personal_rating >= 8)


BUILTIN_SMART_LISTS: tuple[SmartListDefinition, ...] = (
    SmartListDefinition(
        SMART_ID_UNWATCHED_FAVORITES,
        "unwatched_favorites",
        "İzlenmemiş favoriler",
        "Favoriye alınmış ve henüz izlenmemiş içerikler",
        _unwatched_favorite,
    ),
    SmartListDefinition(
        SMART_ID_FAVORITES,
        "favorites",
        "Favoriler",
        "Favoriye alınmış tüm film ve diziler",
        _favorite,
    ),
    SmartListDefinition(
        SMART_ID_WATCHING,
        "watching",
        "İzleniyor",
        "Şu an izlenen içerikler",
        _watching,
    ),
    SmartListDefinition(
        SMART_ID_PLANNED,
        "planned",
        "İzlenecek",
        "Planlanan film ve diziler",
        _planned,
    ),
    SmartListDefinition(
        SMART_ID_HIGHLY_RATED,
        "highly_rated",
        "Yüksek puanlı",
        "Kişisel puanı 8 ve üzeri olanlar",
        _highly_rated,
    ),
)


def is_smart_list_id(list_id: int) -> bool:
    """True for built-in smart lists and virtual per-tag lists."""
    return list_id < 0


def tag_list_id(tag_id: int) -> int:
    """Map a persisted tag primary key onto a virtual smart-list id."""
    if tag_id <= 0:
        raise ValueError("Geçersiz etiket")
    return _TAG_LIST_BASE - tag_id


def tag_id_from_list(list_id: int) -> int | None:
    """Return the tag id for a virtual tag list, otherwise None."""
    if list_id >= _TAG_LIST_BASE:
        return None
    return _TAG_LIST_BASE - list_id


def builtin_by_id(list_id: int) -> SmartListDefinition | None:
    return next((item for item in BUILTIN_SMART_LISTS if item.id == list_id), None)
