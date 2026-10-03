"""Small repositories that leave transaction control to their caller."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from izlek.db.models import (
    CustomList,
    CustomListItem,
    Episode,
    EpisodeProgress,
    MediaItem,
    MediaType,
    Season,
    TrackingStatus,
    UserMedia,
    utc_now,
)

_MEDIA_METADATA = frozenset(
    {
        "original_language",
        "overview",
        "poster_path",
        "backdrop_path",
        "release_date",
        "first_air_date",
        "runtime",
        "metadata_json",
        "last_synced_at",
    }
)
_SEASON_METADATA = frozenset(
    {
        "tmdb_season_id",
        "name",
        "overview",
        "poster_path",
        "air_date",
        "last_synced_at",
    }
)
_EPISODE_METADATA = frozenset(
    {"tmdb_episode_id", "name", "overview", "air_date", "runtime", "still_path"}
)


def _apply_metadata(record: object, values: dict, allowed: frozenset[str]) -> None:
    unknown = values.keys() - allowed
    if unknown:
        raise ValueError(f"Bilinmeyen metadata alanları: {', '.join(sorted(unknown))}")
    for key, value in values.items():
        setattr(record, key, value)


class MediaRepository:
    """Access TMDb metadata without modifying user-owned tables."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, media_id: int) -> MediaItem | None:
        return self.session.get(MediaItem, media_id)

    def get_by_tmdb(self, tmdb_id: int, media_type: MediaType) -> MediaItem | None:
        return self.session.scalar(
            select(MediaItem).where(
                MediaItem.tmdb_id == tmdb_id, MediaItem.media_type == media_type
            )
        )

    def list_all(self) -> list[MediaItem]:
        return list(self.session.scalars(select(MediaItem).order_by(MediaItem.id)))

    def list_local_media(
        self, media_type: MediaType
    ) -> list[tuple[MediaItem, UserMedia]]:
        """Return local items with a tracking status or favorite flag."""
        return list(
            self.session.execute(
                select(MediaItem, UserMedia)
                .join(UserMedia, UserMedia.media_id == MediaItem.id)
                .where(
                    MediaItem.media_type == media_type,
                    (UserMedia.status.is_not(None)) | UserMedia.favorite,
                )
                .order_by(MediaItem.id)
            )
        )

    def upsert(
        self,
        tmdb_id: int,
        media_type: MediaType,
        original_title: str,
        **metadata: object,
    ) -> MediaItem:
        """Update metadata by TMDb identity, retaining the existing local ID."""
        unknown = metadata.keys() - _MEDIA_METADATA
        if unknown:
            raise ValueError(
                f"Bilinmeyen metadata alanları: {', '.join(sorted(unknown))}"
            )
        item = self.get_by_tmdb(tmdb_id, media_type)
        if item is None:
            item = MediaItem(
                tmdb_id=tmdb_id, media_type=media_type, original_title=original_title
            )
            self.session.add(item)
        else:
            item.original_title = original_title
        _apply_metadata(item, metadata, _MEDIA_METADATA)
        self.session.flush()
        return item

    def delete(self, media_id: int) -> bool:
        item = self.get(media_id)
        if item is None:
            return False
        self.session.delete(item)
        self.session.flush()
        return True


class UserMediaRepository:
    """Read and change status and favorites independently."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, media_id: int) -> UserMedia | None:
        return self.session.get(UserMedia, media_id)

    def _get_or_create(self, media_id: int) -> UserMedia:
        item = self.get(media_id)
        if item is None:
            item = UserMedia(media_id=media_id, status=None, favorite=False)
            self.session.add(item)
        return item

    def set_status(
        self, media_id: int, status: TrackingStatus | None, *, manual: bool = True
    ) -> UserMedia:
        """Persist a selection; automatic updates never replace manual choices."""
        item = self._get_or_create(media_id)
        if not manual and item.status_is_manual:
            return item
        item.status = status
        item.status_is_manual = manual and status is not None
        self.session.flush()
        return item

    def set_favorite(self, media_id: int, favorite: bool) -> UserMedia:
        item = self._get_or_create(media_id)
        item.favorite = favorite
        self.session.flush()
        return item

    def remove(self, media_id: int) -> bool:
        item = self.get(media_id)
        if item is None:
            return False
        self.session.delete(item)
        self.session.flush()
        return True


class StatisticsRepository:
    """Read local tracking and metadata rows for aggregate statistics."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def media_with_tracking(self) -> list[tuple[MediaItem, UserMedia]]:
        return list(
            self.session.execute(
                select(MediaItem, UserMedia).join(
                    UserMedia, UserMedia.media_id == MediaItem.id
                )
            )
        )

    def watched_episodes(self) -> list[Episode]:
        return list(
            self.session.scalars(
                select(Episode)
                .join(EpisodeProgress, EpisodeProgress.episode_id == Episode.id)
                .where(EpisodeProgress.watched.is_(True))
            )
        )


class TransferRepository:
    """Read all portable records used by İzlek JSON import and export."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def media(self) -> list[MediaItem]:
        return list(self.session.scalars(select(MediaItem).order_by(MediaItem.id)))

    def tracking(self) -> list[UserMedia]:
        return list(
            self.session.scalars(select(UserMedia).order_by(UserMedia.media_id))
        )

    def seasons(self) -> list[Season]:
        return list(
            self.session.scalars(
                select(Season).order_by(Season.media_id, Season.season_number)
            )
        )

    def episodes(self) -> list[Episode]:
        return list(
            self.session.scalars(
                select(Episode).order_by(Episode.season_id, Episode.episode_number)
            )
        )

    def episode_progress(self) -> list[EpisodeProgress]:
        return list(
            self.session.scalars(
                select(EpisodeProgress).order_by(EpisodeProgress.episode_id)
            )
        )

    def lists(self) -> list[CustomList]:
        return list(
            self.session.scalars(
                select(CustomList).order_by(CustomList.sort_order, CustomList.id)
            )
        )

    def list_items(self) -> list[CustomListItem]:
        return list(
            self.session.scalars(
                select(CustomListItem).order_by(
                    CustomListItem.list_id,
                    CustomListItem.sort_order,
                    CustomListItem.media_id,
                )
            )
        )


class SeasonRepository:
    """Access TV season metadata, keyed by media and season number."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, season_id: int) -> Season | None:
        return self.session.get(Season, season_id)

    def list_for_media(self, media_id: int) -> list[Season]:
        return list(
            self.session.scalars(
                select(Season)
                .where(Season.media_id == media_id)
                .order_by(Season.season_number)
            )
        )

    def upsert(self, media_id: int, season_number: int, **metadata: object) -> Season:
        media = self.session.get(MediaItem, media_id)
        if media is None:
            raise LookupError(f"Medya bulunamadı: {media_id}")
        if media.media_type != MediaType.TV:
            raise ValueError("Sezon yalnızca diziye eklenebilir")
        season = self.session.scalar(
            select(Season).where(
                Season.media_id == media_id, Season.season_number == season_number
            )
        )
        if season is None:
            season = Season(media_id=media_id, season_number=season_number)
            self.session.add(season)
        _apply_metadata(season, metadata, _SEASON_METADATA)
        self.session.flush()
        return season

    def delete(self, season_id: int) -> bool:
        season = self.get(season_id)
        if season is None:
            return False
        self.session.delete(season)
        self.session.flush()
        return True


class EpisodeRepository:
    """Keep episode metadata separate from local watched progress."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, episode_id: int) -> Episode | None:
        return self.session.get(Episode, episode_id)

    def list_for_season(self, season_id: int) -> list[Episode]:
        return list(
            self.session.scalars(
                select(Episode)
                .where(Episode.season_id == season_id)
                .order_by(Episode.episode_number)
            )
        )

    def list_for_season_with_progress(
        self, season_id: int
    ) -> list[tuple[Episode, EpisodeProgress | None]]:
        """Return season episodes and optional progress in one query."""
        return list(
            self.session.execute(
                select(Episode, EpisodeProgress)
                .outerjoin(
                    EpisodeProgress, EpisodeProgress.episode_id == Episode.id
                )
                .where(Episode.season_id == season_id)
                .order_by(Episode.episode_number)
            )
        )

    def list_for_media_with_progress(
        self, media_id: int
    ) -> list[tuple[Season, Episode, EpisodeProgress | None]]:
        """Return every episode for a show without per-season/progress queries."""
        return list(
            self.session.execute(
                select(Season, Episode, EpisodeProgress)
                .join(Episode, Episode.season_id == Season.id)
                .outerjoin(
                    EpisodeProgress, EpisodeProgress.episode_id == Episode.id
                )
                .where(Season.media_id == media_id)
                .order_by(Season.season_number, Episode.episode_number)
            )
        )

    def upsert(
        self, season_id: int, episode_number: int, **metadata: object
    ) -> Episode:
        episode = self.session.scalar(
            select(Episode).where(
                Episode.season_id == season_id,
                Episode.episode_number == episode_number,
            )
        )
        if episode is None:
            episode = Episode(season_id=season_id, episode_number=episode_number)
            self.session.add(episode)
        _apply_metadata(episode, metadata, _EPISODE_METADATA)
        self.session.flush()
        return episode

    def get_progress(self, episode_id: int) -> EpisodeProgress | None:
        return self.session.get(EpisodeProgress, episode_id)

    def list_continue_candidates(
        self,
        media_ids: set[int] | None = None,
    ) -> list[
        tuple[MediaItem, UserMedia | None, Season, Episode, EpisodeProgress | None]
    ]:
        """Return regular TV episodes with tracking state in one local query."""
        query = (
            select(MediaItem, UserMedia, Season, Episode, EpisodeProgress)
            .join(Season, Season.media_id == MediaItem.id)
            .join(Episode, Episode.season_id == Season.id)
            .outerjoin(UserMedia, UserMedia.media_id == MediaItem.id)
            .outerjoin(EpisodeProgress, EpisodeProgress.episode_id == Episode.id)
            .where(MediaItem.media_type == MediaType.TV, Season.season_number > 0)
            .order_by(
                MediaItem.id,
                Season.season_number,
                Episode.episode_number,
                Episode.id,
            )
        )
        if media_ids is not None:
            query = query.where(MediaItem.id.in_(media_ids))
        return list(self.session.execute(query))

    def set_watched(self, episode_id: int, watched: bool) -> EpisodeProgress:
        progress = self.get_progress(episode_id)
        if progress is None:
            progress = EpisodeProgress(episode_id=episode_id)
            self.session.add(progress)
        if watched and not progress.watched:
            progress.watched_at = utc_now()
        elif not watched:
            progress.watched_at = None
        progress.watched = watched
        self.session.flush()
        return progress

    def delete(self, episode_id: int) -> bool:
        episode = self.get(episode_id)
        if episode is None:
            return False
        self.session.delete(episode)
        self.session.flush()
        return True


class CustomListRepository:
    """Create ordered lists and membership without duplicating items."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, list_id: int) -> CustomList | None:
        return self.session.get(CustomList, list_id)

    def list_all(self) -> list[CustomList]:
        return list(
            self.session.scalars(
                select(CustomList).order_by(CustomList.sort_order, CustomList.id)
            )
        )

    def create(self, name: str, sort_order: int = 0) -> CustomList:
        item = CustomList(name=name, sort_order=sort_order)
        self.session.add(item)
        self.session.flush()
        return item

    def rename(self, list_id: int, name: str) -> CustomList:
        item = self.get(list_id)
        if item is None:
            raise LookupError(f"Liste bulunamadı: {list_id}")
        item.name = name
        self.session.flush()
        return item

    def set_position(self, list_id: int, sort_order: int) -> CustomList:
        item = self.get(list_id)
        if item is None:
            raise LookupError(f"Liste bulunamadı: {list_id}")
        item.sort_order = sort_order
        self.session.flush()
        return item

    def delete(self, list_id: int) -> bool:
        item = self.get(list_id)
        if item is None:
            return False
        self.session.delete(item)
        self.session.flush()
        return True

    def list_items(self, list_id: int) -> list[CustomListItem]:
        return list(
            self.session.scalars(
                select(CustomListItem)
                .where(CustomListItem.list_id == list_id)
                .order_by(CustomListItem.sort_order, CustomListItem.media_id)
            )
        )

    def list_all_items(self) -> list[CustomListItem]:
        """Return all memberships for bulk list presentation."""
        return list(
            self.session.scalars(
                select(CustomListItem).order_by(
                    CustomListItem.list_id,
                    CustomListItem.sort_order,
                    CustomListItem.media_id,
                )
            )
        )

    def list_names_for_media(self, media_id: int) -> list[str]:
        """Read a media item's list names with one joined query."""
        return list(
            self.session.scalars(
                select(CustomList.name)
                .join(CustomListItem, CustomListItem.list_id == CustomList.id)
                .where(CustomListItem.media_id == media_id)
                .order_by(CustomList.sort_order, CustomList.id)
            )
        )

    def add_item(
        self, list_id: int, media_id: int, sort_order: int = 0
    ) -> CustomListItem:
        item = self.session.get(CustomListItem, (list_id, media_id))
        if item is None:
            item = CustomListItem(
                list_id=list_id, media_id=media_id, sort_order=sort_order
            )
            self.session.add(item)
        else:
            item.sort_order = sort_order
        self.session.flush()
        return item

    def set_item_position(
        self, list_id: int, media_id: int, sort_order: int
    ) -> CustomListItem:
        item = self.session.get(CustomListItem, (list_id, media_id))
        if item is None:
            raise LookupError(f"Liste öğesi bulunamadı: {list_id}/{media_id}")
        item.sort_order = sort_order
        self.session.flush()
        return item

    def remove_item(self, list_id: int, media_id: int) -> bool:
        item = self.session.get(CustomListItem, (list_id, media_id))
        if item is None:
            return False
        self.session.delete(item)
        self.session.flush()
        return True
