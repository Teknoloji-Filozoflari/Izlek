"""Versioned, portable İzlek JSON schema."""

from datetime import date, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 1


class TransferModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MediaRef(TransferModel):
    tmdb_id: int = Field(gt=0)
    media_type: Literal["MOVIE", "TV"]


class EpisodeMetadata(TransferModel):
    episode_number: int = Field(ge=0)
    tmdb_episode_id: int | None = None
    name: str | None = None
    overview: str | None = None
    air_date: date | None = None
    runtime: int | None = Field(default=None, ge=0)
    still_path: str | None = None


class SeasonMetadata(TransferModel):
    season_number: int = Field(ge=0)
    tmdb_season_id: int | None = None
    name: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    air_date: date | None = None
    last_synced_at: datetime | None = None
    episodes: list[EpisodeMetadata] = Field(default_factory=list)


class MediaExport(MediaRef):
    original_title: str = Field(min_length=1, max_length=500)
    original_language: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    release_date: date | None = None
    first_air_date: date | None = None
    runtime: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] | None = None
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    seasons: list[SeasonMetadata] = Field(default_factory=list)


class TrackingExport(MediaRef):
    status: Literal["PLANNED", "WATCHING", "WATCHED"] | None = None
    status_is_manual: bool = False
    added_at: datetime
    updated_at: datetime


class EpisodeProgressExport(MediaRef):
    media_type: Literal["TV"] = "TV"
    season_number: int = Field(ge=0)
    episode_number: int = Field(ge=0)
    watched: bool
    watched_at: datetime | None = None


class ListItemExport(MediaRef):
    sort_order: int = Field(ge=0)
    added_at: datetime


class CustomListExport(TransferModel):
    name: str = Field(min_length=1, max_length=200)
    sort_order: int = Field(ge=0)
    created_at: datetime
    items: list[ListItemExport] = Field(default_factory=list)


class IzlekExport(TransferModel):
    schema_version: Literal[SCHEMA_VERSION]
    exported_at: datetime
    app_version: str
    media: list[MediaExport]
    tracking: list[TrackingExport]
    episodes: list[EpisodeProgressExport]
    favorites: list[MediaRef]
    lists: list[CustomListExport]

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        if any(item.media_type == "MOVIE" and item.seasons for item in self.media):
            raise ValueError("Film kaydı sezon metadata'sı içeremez")
        media_keys = {(item.media_type, item.tmdb_id) for item in self.media}
        episode_keys = {
            (item.tmdb_id, season.season_number, episode.episode_number)
            for item in self.media
            if item.media_type == "TV"
            for season in item.seasons
            for episode in season.episodes
        }
        references = [*self.tracking, *self.favorites]
        references.extend(
            item for custom_list in self.lists for item in custom_list.items
        )
        if any(
            (item.media_type, item.tmdb_id) not in media_keys
            for item in references
        ):
            raise ValueError("Medya referansı export içeriğinde bulunamadı")
        if any(
            (item.tmdb_id, item.season_number, item.episode_number)
            not in episode_keys
            for item in self.episodes
        ):
            raise ValueError("Bölüm ilerlemesi için metadata bulunamadı")
        return self
