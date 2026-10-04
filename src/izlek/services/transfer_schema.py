"""Versioned, portable İzlek JSON schema."""

from datetime import date, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from izlek.tmdb.models import (
    MovieCredits,
    MovieDetail,
    MovieSearchResults,
    MovieVideos,
    MovieWatchProviders,
    TvDetail,
    TvSearchResults,
)

SCHEMA_VERSION = 1
_SQLITE_MAX_INT = 2**63 - 1


class TransferModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MediaRef(TransferModel):
    tmdb_id: int = Field(gt=0, le=_SQLITE_MAX_INT)
    media_type: Literal["MOVIE", "TV"]


class EpisodeMetadata(TransferModel):
    episode_number: int = Field(ge=0, le=_SQLITE_MAX_INT)
    tmdb_episode_id: int | None = Field(default=None, gt=0, le=_SQLITE_MAX_INT)
    name: str | None = None
    overview: str | None = None
    air_date: date | None = None
    runtime: int | None = Field(default=None, ge=0, le=_SQLITE_MAX_INT)
    still_path: str | None = None


class SeasonMetadata(TransferModel):
    season_number: int = Field(ge=0, le=_SQLITE_MAX_INT)
    tmdb_season_id: int | None = Field(default=None, gt=0, le=_SQLITE_MAX_INT)
    name: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    air_date: date | None = None
    last_synced_at: datetime | None = None
    episodes: list[EpisodeMetadata] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_episode_identities(self) -> Self:
        numbers = [episode.episode_number for episode in self.episodes]
        ids = [
            episode.tmdb_episode_id
            for episode in self.episodes
            if episode.tmdb_episode_id is not None
        ]
        if len(numbers) != len(set(numbers)) or len(ids) != len(set(ids)):
            raise ValueError("Sezonda yinelenen bölüm kimliği var")
        return self


class MediaExport(MediaRef):
    original_title: str = Field(min_length=1, max_length=500)
    original_language: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    release_date: date | None = None
    first_air_date: date | None = None
    runtime: int | None = Field(default=None, ge=0, le=_SQLITE_MAX_INT)
    metadata: dict[str, Any] | None = None
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    seasons: list[SeasonMetadata] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_metadata(self) -> Self:
        numbers = [season.season_number for season in self.seasons]
        ids = [
            season.tmdb_season_id
            for season in self.seasons
            if season.tmdb_season_id is not None
        ]
        if len(numbers) != len(set(numbers)) or len(ids) != len(set(ids)):
            raise ValueError("Dizide yinelenen sezon kimliği var")
        models = {
            "detail": MovieDetail if self.media_type == "MOVIE" else TvDetail,
            "credits": MovieCredits,
            "videos": MovieVideos,
            "providers": MovieWatchProviders,
            "similar": MovieSearchResults
            if self.media_type == "MOVIE"
            else TvSearchResults,
            "recommendations": MovieSearchResults
            if self.media_type == "MOVIE"
            else TvSearchResults,
        }
        for key, model in models.items():
            if self.metadata and self.metadata.get(key) is not None:
                section = model.model_validate(self.metadata[key])
                if hasattr(section, "id") and section.id != self.tmdb_id:
                    raise ValueError("Metadata kimliği medya referansıyla uyuşmuyor")
        return self


class TrackingExport(MediaRef):
    status: Literal["PLANNED", "WATCHING", "WATCHED"] | None = None
    status_is_manual: bool = False
    added_at: datetime
    updated_at: datetime


class EpisodeProgressExport(MediaRef):
    media_type: Literal["TV"] = "TV"
    season_number: int = Field(ge=0, le=_SQLITE_MAX_INT)
    episode_number: int = Field(ge=0, le=_SQLITE_MAX_INT)
    watched: bool
    watched_at: datetime | None = None


class ListItemExport(MediaRef):
    sort_order: int = Field(ge=0, le=_SQLITE_MAX_INT)
    added_at: datetime


class CustomListExport(TransferModel):
    name: str = Field(min_length=1, max_length=200)
    sort_order: int = Field(ge=0, le=_SQLITE_MAX_INT)
    created_at: datetime
    items: list[ListItemExport] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Liste adı boş olamaz")
        return value


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
            (item.media_type, item.tmdb_id) not in media_keys for item in references
        ):
            raise ValueError("Medya referansı export içeriğinde bulunamadı")
        if any(
            (item.tmdb_id, item.season_number, item.episode_number) not in episode_keys
            for item in self.episodes
        ):
            raise ValueError("Bölüm ilerlemesi için metadata bulunamadı")
        return self
