"""Typed responses for the TMDb endpoints used by İzlek."""

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Ignore fields added by TMDb while validating fields we use."""

    model_config = ConfigDict(extra="ignore")


class ImageConfiguration(ApiModel):
    secure_base_url: str
    poster_sizes: list[str]
    backdrop_sizes: list[str]
    still_sizes: list[str] = Field(default_factory=list)


class Configuration(ApiModel):
    images: ImageConfiguration
    change_keys: list[str] = Field(default_factory=list)


class MovieSummary(ApiModel):
    id: int
    title: str
    original_title: str
    overview: str = ""
    poster_path: str | None = None
    backdrop_path: str | None = None
    release_date: str | None = None
    vote_average: float = 0.0
    vote_count: int = 0


class TvSummary(ApiModel):
    id: int
    name: str
    original_name: str
    overview: str = ""
    poster_path: str | None = None
    backdrop_path: str | None = None
    first_air_date: str | None = None
    vote_average: float = 0.0
    vote_count: int = 0


class MovieSearchResults(ApiModel):
    page: int
    results: list[MovieSummary]
    total_pages: int
    total_results: int


class TvSearchResults(ApiModel):
    page: int
    results: list[TvSummary]
    total_pages: int
    total_results: int


class Genre(ApiModel):
    id: int
    name: str


class MovieDetail(MovieSummary):
    runtime: int | None = None
    genres: list[Genre] = Field(default_factory=list)
    original_language: str | None = None
    production_companies: list["ProductionCompany"] = Field(default_factory=list)
    production_countries: list["ProductionCountry"] = Field(default_factory=list)


class ProductionCompany(ApiModel):
    id: int
    name: str


class ProductionCountry(ApiModel):
    iso_3166_1: str
    name: str


class CastMember(ApiModel):
    id: int
    name: str
    character: str = ""
    order: int = 0
    profile_path: str | None = None


class CrewMember(ApiModel):
    id: int
    name: str
    job: str


class MovieCredits(ApiModel):
    id: int
    cast: list[CastMember] = Field(default_factory=list)
    crew: list[CrewMember] = Field(default_factory=list)


class Video(ApiModel):
    key: str
    site: str
    type: str
    name: str
    official: bool = False


class MovieVideos(ApiModel):
    id: int
    results: list[Video] = Field(default_factory=list)


class WatchProvider(ApiModel):
    provider_id: int
    provider_name: str
    logo_path: str | None = None


class WatchProviderRegion(ApiModel):
    link: str | None = None
    flatrate: list[WatchProvider] = Field(default_factory=list)
    free: list[WatchProvider] = Field(default_factory=list)
    ads: list[WatchProvider] = Field(default_factory=list)
    rent: list[WatchProvider] = Field(default_factory=list)
    buy: list[WatchProvider] = Field(default_factory=list)


class MovieWatchProviders(ApiModel):
    id: int
    results: dict[str, WatchProviderRegion] = Field(default_factory=dict)


class SeasonSummary(ApiModel):
    id: int
    season_number: int
    name: str
    episode_count: int = 0
    poster_path: str | None = None
    air_date: str | None = None


class TvDetail(TvSummary):
    number_of_seasons: int = 0
    number_of_episodes: int = 0
    seasons: list[SeasonSummary] = Field(default_factory=list)
    genres: list[Genre] = Field(default_factory=list)
    original_language: str | None = None
    last_air_date: str | None = None
    status: str = ""
    created_by: list["Creator"] = Field(default_factory=list)
    production_companies: list[ProductionCompany] = Field(default_factory=list)
    production_countries: list[ProductionCountry] = Field(default_factory=list)


class Creator(ApiModel):
    id: int
    name: str


class Episode(ApiModel):
    id: int
    episode_number: int
    name: str
    original_name: str | None = None
    overview: str = ""
    air_date: str | None = None
    runtime: int | None = None
    still_path: str | None = None


class SeasonDetail(ApiModel):
    id: int
    season_number: int
    name: str
    overview: str = ""
    poster_path: str | None = None
    air_date: str | None = None
    episodes: list[Episode]
