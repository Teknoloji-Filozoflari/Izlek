"""Movie metadata and local tracking transactions."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from threading import Lock
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus, utc_now
from izlek.repositories.local import (
    CustomListRepository,
    MediaRepository,
    UserMediaRepository,
)
from izlek.services.custom_lists import CustomListsService
from izlek.services.metadata_freshness import metadata_is_fresh
from izlek.services.metadata_retention import merge_remote_metadata
from izlek.services.provider_presentation import present_providers
from izlek.tmdb.client import NetworkError, TmdbClient, TMDbError
from izlek.tmdb.models import MovieDetail, MovieSearchResults, MovieVideos

_OPTIONAL = (
    ("credits", "movie_credits"),
    ("videos", "movie_videos"),
    ("similar", "movie_similar"),
    ("recommendations", "movie_recommendations"),
    ("providers", "movie_watch_providers"),
)


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _trailer_url(videos: MovieVideos | None) -> str:
    if videos is None:
        return ""
    choices = [
        video for video in videos.results
        if video.site == "YouTube" and video.type == "Trailer"
        and video.key.replace("-", "").replace("_", "").isalnum()
    ]
    if not choices:
        return ""
    selected = next((video for video in choices if video.official), choices[0])
    return "https://www.youtube.com/watch?v=" + selected.key


class MovieDetailService:
    """Keep remote movie metadata separate from durable personal state."""

    def __init__(
        self,
        client: TmdbClient,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        self.client = client
        self._factory = session_factory
        self._owned_engine: Engine | None = None
        self._session_lock = Lock()

    def _sessions(self) -> sessionmaker[Session]:
        with self._session_lock:
            if self._factory is None:
                self._owned_engine = initialize_database()
                self._factory = create_session_factory(self._owned_engine)
        return self._factory

    def close(self) -> None:
        """Dispose the database connection only when this service opened it."""
        if self._owned_engine is not None:
            self._owned_engine.dispose()

    def load(self, movie_id: int) -> dict[str, Any]:
        """Fetch movie sections concurrently and persist successful metadata."""
        try:
            with ThreadPoolExecutor(max_workers=6) as executor:
                main = executor.submit(self.client.movie, movie_id)
                extras = {
                    name: executor.submit(getattr(self.client, method), movie_id)
                    for name, method in _OPTIONAL
                }
                detail = main.result()
                extra_data: dict[str, Any] = {}
                for name, future in extras.items():
                    try:
                        extra_data[name] = future.result().model_dump(mode="json")
                    except TMDbError:
                        pass
        except NetworkError:
            cached = self.cached(movie_id)
            if cached is not None:
                return cached
            raise
        blob = {"detail": detail.model_dump(mode="json"), **extra_data}
        sessions = self._sessions()
        with sessions.begin() as session:
            repo = MediaRepository(session)
            existing = repo.get_by_tmdb(movie_id, MediaType.MOVIE)
            synced_at = utc_now()
            blob = merge_remote_metadata(existing, blob, synced_at)
            repo.upsert(
                movie_id,
                MediaType.MOVIE,
                detail.original_title,
                original_language=detail.original_language,
                overview=detail.overview,
                poster_path=detail.poster_path,
                backdrop_path=detail.backdrop_path,
                release_date=_date(detail.release_date),
                runtime=detail.runtime,
                metadata_json=blob,
                last_synced_at=synced_at,
            )
        return self.cached(movie_id) or {}

    def needs_refresh(self, movie_id: int, *, now: datetime | None = None) -> bool:
        """Check the saved timestamp without making a network request."""
        with self._sessions()() as session:
            item = MediaRepository(session).get_by_tmdb(movie_id, MediaType.MOVIE)
            return item is None or not metadata_is_fresh(
                item.last_synced_at, now=now
            )

    def cached(self, movie_id: int) -> dict[str, Any] | None:
        """Read the last saved movie detail and local user state."""
        sessions = self._sessions()
        with sessions() as session:
            item = MediaRepository(session).get_by_tmdb(movie_id, MediaType.MOVIE)
            if item is None or not (item.metadata_json or {}).get("detail"):
                return None
            user = UserMediaRepository(session).get(item.id)
            lists = CustomListRepository(session).list_all()
            list_repo = CustomListRepository(session)
            selected = list_repo.list_names_for_media(item.id)
            state = {
                "status": user.status.value if user and user.status else "",
                "favorite": bool(user.favorite) if user else False,
                "lists": selected,
                "availableLists": [entry.name for entry in lists],
            }
            return self._presentation(item.metadata_json, state)

    def _presentation(
        self, blob: dict[str, Any], state: dict[str, Any]
    ) -> dict[str, Any]:
        detail = MovieDetail.model_validate(blob["detail"])
        credits = blob.get("credits") or {}
        videos = (
            MovieVideos.model_validate(blob["videos"])
            if blob.get("videos")
            else None
        )
        region = (blob.get("providers") or {}).get("results", {}).get("TR", {})
        groups, provider_link = present_providers(region)
        def related(key: str) -> list[dict[str, Any]]:
            data = blob.get(key)
            if not data:
                return []
            page = MovieSearchResults.model_validate(data)
            return [
                {
                    "id": movie.id,
                    "mediaType": "movie",
                    "title": movie.original_title,
                    "year": movie.release_date[:4] if movie.release_date else "",
                    "posterPath": movie.poster_path or "",
                    "poster": "",
                }
                for movie in page.results[:8]
            ]

        cast = sorted(
            credits.get("cast", []), key=lambda member: member.get("order", 0)
        )
        directors = [
            member["name"] for member in credits.get("crew", [])
            if member.get("job") == "Director"
        ]
        return {
            "id": detail.id,
            "title": detail.original_title,
            "year": detail.release_date[:4] if detail.release_date else "",
            "runtime": detail.runtime or 0,
            "genres": [genre.name for genre in detail.genres],
            "score": round(detail.vote_average, 1),
            "overview": detail.overview,
            "posterPath": detail.poster_path or "",
            "backdropPath": detail.backdrop_path or "",
            "poster": "",
            "backdrop": "",
            "cast": [
                {
                    "name": member["name"],
                    "character": member.get("character", ""),
                    "profilePath": member.get("profile_path") or "",
                }
                for member in cast[:12]
            ],
            "directors": directors,
            "companies": [company.name for company in detail.production_companies],
            "countries": [country.name for country in detail.production_countries],
            "providers": groups,
            "providerLink": provider_link,
            "trailerUrl": _trailer_url(videos),
            "similar": related("similar"),
            "recommendations": related("recommendations"),
            **state,
        }

    def set_status(self, movie_id: int, status: str | None) -> dict[str, Any]:
        """Set tracking status; None removes library membership only."""
        selected = TrackingStatus(status) if status is not None else None
        with self._sessions().begin() as session:
            media = MediaRepository(session).get_by_tmdb(movie_id, MediaType.MOVIE)
            if media is None:
                raise LookupError("Film yerel veritabanında yok")
            UserMediaRepository(session).set_status(media.id, selected)
        return self.cached(movie_id) or {}

    def set_favorite(self, movie_id: int, favorite: bool) -> dict[str, Any]:
        """Persist favorite independently of tracking status."""
        with self._sessions().begin() as session:
            media = MediaRepository(session).get_by_tmdb(movie_id, MediaType.MOVIE)
            if media is None:
                raise LookupError("Film yerel veritabanında yok")
            UserMediaRepository(session).set_favorite(media.id, favorite)
        return self.cached(movie_id) or {}

    def add_to_list(self, movie_id: int, name: str) -> dict[str, Any]:
        """Add a movie to a named list, creating the list when needed."""
        CustomListsService(self._sessions()).add_by_name("movie", movie_id, name)
        return self.cached(movie_id) or {}
