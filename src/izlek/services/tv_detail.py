"""TV metadata and durable local episode progress."""

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
    EpisodeRepository,
    MediaRepository,
    SeasonRepository,
    UserMediaRepository,
)
from izlek.services.custom_lists import CustomListsService
from izlek.services.metadata_freshness import metadata_is_fresh
from izlek.services.metadata_retention import merge_remote_metadata
from izlek.services.movie_detail import _trailer_url
from izlek.services.provider_presentation import present_providers
from izlek.services.tv_status import TvProgress, automatic_status
from izlek.tmdb.client import NetworkError, TmdbClient, TMDbError
from izlek.tmdb.models import MovieVideos, TvDetail, TvSearchResults

_OPTIONAL = (
    ("credits", "tv_credits"),
    ("videos", "tv_videos"),
    ("similar", "tv_similar"),
    ("recommendations", "tv_recommendations"),
    ("providers", "tv_watch_providers"),
)
_STATUS_LABELS = {
    "Returning Series": "Devam ediyor",
    "Planned": "Planlandı",
    "In Production": "Yapım aşamasında",
    "Ended": "Sona erdi",
    "Canceled": "İptal edildi",
    "Pilot": "Pilot",
}


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


class TvDetailService:
    """Persist remote season metadata without touching local episode progress."""

    def __init__(
        self, client: TmdbClient, session_factory: sessionmaker[Session] | None = None
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
        if self._owned_engine is not None:
            self._owned_engine.dispose()

    def _progress(
        self, session: Session, media_id: int, detail: TvDetail
    ) -> tuple[TvProgress, dict[int, int]]:
        """Count released episodes and detect incomplete local season metadata."""
        rows = EpisodeRepository(session).list_for_media_with_progress(media_id)
        by_season: dict[int, list[tuple[Any, Any]]] = {}
        for season, episode, progress in rows:
            by_season.setdefault(season.season_number, []).append((episode, progress))
        today = date.today()
        watched_count = aired_count = unwatched_aired_count = missing = 0
        season_watched: dict[int, int] = {}
        for summary in detail.seasons:
            local = by_season.get(summary.season_number, [])
            missing += max(0, summary.episode_count - len(local))
            season_watched[summary.season_number] = 0
            for episode, progress in local:
                watched = bool(progress and progress.watched)
                watched_count += watched
                season_watched[summary.season_number] += watched
                if episode.air_date is not None and episode.air_date <= today:
                    aired_count += 1
                    unwatched_aired_count += not watched
        return (
            TvProgress(
                watched_count,
                aired_count,
                unwatched_aired_count,
                missing,
                sum(season.episode_count for season in detail.seasons),
            ),
            season_watched,
        )

    def _sync_status(
        self, session: Session, media_id: int, *, explicit_unwatch: bool
    ) -> None:
        """Apply automatic status in the same transaction as a progress change."""
        media = MediaRepository(session).get(media_id)
        if media is None:
            raise LookupError("Dizi bulunamadı")
        blob = media.metadata_json or {}
        if blob.get("detail"):
            detail = TvDetail.model_validate(blob["detail"])
            progress, _ = self._progress(session, media_id, detail)
        else:
            # Portable imports may contain progress without full TMDb details.
            # Completion cannot be inferred from a partially known episode list.
            rows = EpisodeRepository(session).list_for_media_with_progress(media_id)
            today = date.today()
            progress = TvProgress(
                watched_count=sum(
                    bool(state and state.watched) for _, _, state in rows
                ),
                aired_count=sum(
                    episode.air_date is not None and episode.air_date <= today
                    for _, episode, _ in rows
                ),
                unwatched_aired_count=sum(
                    episode.air_date is not None
                    and episode.air_date <= today
                    and not (state and state.watched)
                    for _, episode, state in rows
                ),
                missing_metadata_count=1,
            )
        repository = UserMediaRepository(session)
        user = repository.get(media_id)
        current = user.status if user else None
        selected = automatic_status(
            current,
            manual=bool(user and user.status_is_manual),
            progress=progress,
            explicit_unwatch=explicit_unwatch,
        )
        if selected != current or (user and user.status_is_manual):
            repository.set_status(
                media_id, selected, manual=False, override_manual=True
            )

    def load(self, tv_id: int) -> dict[str, Any]:
        """Fetch show sections, merge optional metadata, and keep local state."""
        try:
            with ThreadPoolExecutor(max_workers=6) as executor:
                main = executor.submit(self.client.tv, tv_id)
                extras = {
                    name: executor.submit(getattr(self.client, method), tv_id)
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
            cached = self.cached(tv_id)
            if cached is not None:
                return cached
            raise
        blob = {"detail": detail.model_dump(mode="json"), **extra_data}
        with self._sessions().begin() as session:
            media_repo = MediaRepository(session)
            existing = media_repo.get_by_tmdb(tv_id, MediaType.TV)
            synced_at = utc_now()
            blob = merge_remote_metadata(existing, blob, synced_at)
            media = media_repo.upsert(
                tv_id,
                MediaType.TV,
                detail.original_name,
                original_language=detail.original_language,
                overview=detail.overview,
                poster_path=detail.poster_path,
                backdrop_path=detail.backdrop_path,
                first_air_date=_date(detail.first_air_date),
                metadata_json=blob,
                last_synced_at=synced_at,
            )
            seasons = SeasonRepository(session)
            for season in detail.seasons:
                seasons.upsert(
                    media.id,
                    season.season_number,
                    tmdb_season_id=season.id,
                    name=season.name,
                    poster_path=season.poster_path,
                    air_date=_date(season.air_date),
                )
        return self.cached(tv_id) or {}

    def needs_refresh(self, tv_id: int, *, now: datetime | None = None) -> bool:
        """Check TV detail freshness using only the local media record."""
        with self._sessions()() as session:
            media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
            return media is None or not metadata_is_fresh(media.last_synced_at, now=now)

    def cached(self, tv_id: int) -> dict[str, Any] | None:
        """Read saved TV metadata and user state, including watched counts."""
        with self._sessions()() as session:
            media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
            if media is None or not (media.metadata_json or {}).get("detail"):
                return None
            blob = media.metadata_json
            detail = TvDetail.model_validate(blob["detail"])
            user = UserMediaRepository(session).get(media.id)
            list_repo = CustomListRepository(session)
            available_lists = list_repo.list_all()
            selected_lists = list_repo.list_names_for_media(media.id)
            progress, counts = self._progress(session, media.id, detail)
            credits = blob.get("credits") or {}
            region = (blob.get("providers") or {}).get("results", {}).get("TR", {})
            groups, provider_link = present_providers(region)

            def related(key: str) -> list[dict[str, Any]]:
                if not blob.get(key):
                    return []
                return [
                    {
                        "id": item.id,
                        "mediaType": "tv",
                        "title": item.original_name,
                        "year": item.first_air_date[:4] if item.first_air_date else "",
                        "posterPath": item.poster_path or "",
                        "poster": "",
                    }
                    for item in TvSearchResults.model_validate(blob[key]).results[:8]
                ]

            videos = (
                MovieVideos.model_validate(blob["videos"])
                if blob.get("videos")
                else None
            )
            return {
                "id": detail.id,
                "title": detail.original_name,
                "year": detail.first_air_date[:4] if detail.first_air_date else "",
                "firstAirDate": detail.first_air_date or "",
                "lastAirDate": detail.last_air_date or "",
                "seriesStatus": _STATUS_LABELS.get(detail.status, detail.status),
                "genres": [genre.name for genre in detail.genres],
                "score": round(detail.vote_average, 1),
                "overview": detail.overview,
                "posterPath": detail.poster_path or "",
                "backdropPath": detail.backdrop_path or "",
                "poster": "",
                "backdrop": "",
                "creators": [person.name for person in detail.created_by],
                "cast": [
                    {
                        "name": person["name"],
                        "character": person.get("character", ""),
                        "profilePath": person.get("profile_path") or "",
                    }
                    for person in sorted(
                        credits.get("cast", []), key=lambda item: item.get("order", 0)
                    )[:12]
                ],
                "companies": [company.name for company in detail.production_companies],
                "countries": [country.name for country in detail.production_countries],
                "providers": groups,
                "providerLink": provider_link,
                "trailerUrl": _trailer_url(videos),
                "similar": related("similar"),
                "recommendations": related("recommendations"),
                "seasons": [
                    {
                        "number": season.season_number,
                        "name": season.name,
                        "episodeCount": season.episode_count,
                        "watchedCount": counts.get(season.season_number, 0),
                    }
                    for season in detail.seasons
                ],
                "status": user.status.value if user and user.status else "",
                "statusIsManual": bool(user and user.status_is_manual),
                "favorite": bool(user.favorite) if user else False,
                "lists": selected_lists,
                "availableLists": [entry.name for entry in available_lists],
                "watchedEpisodeCount": progress.watched_count,
                "watchedRegularEpisodeCount": sum(
                    count for number, count in counts.items() if number > 0
                ),
                "totalEpisodeCount": sum(
                    max(0, season.episode_count)
                    for season in detail.seasons
                    if season.season_number > 0
                ),
                "airedEpisodeCount": progress.aired_count,
                "unwatchedAiredCount": progress.unwatched_aired_count,
                "missingEpisodeMetadataCount": progress.missing_metadata_count,
                "newUnwatchedEpisodes": bool(
                    user
                    and user.status == TrackingStatus.WATCHED
                    and progress.unwatched_aired_count > 0
                ),
            }

    def load_season(self, tv_id: int, season_number: int) -> list[dict[str, Any]]:
        """Refresh a season in its original language and return local progress."""
        with self._sessions()() as session:
            media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
            if media is None:
                raise LookupError("Dizi yerel veritabanında yok")
            language = media.original_language or "en"
        try:
            detail = self.client.tv_season(tv_id, season_number, language=language)
        except NetworkError:
            cached = self.cached_season(tv_id, season_number)
            show = self.cached(tv_id)
            expected = (
                next(
                    (
                        entry["episodeCount"]
                        for entry in show["seasons"]
                        if entry["number"] == season_number
                    ),
                    0,
                )
                if show
                else 0
            )
            if cached is not None and len(cached) >= expected:
                return cached
            raise
        with self._sessions().begin() as session:
            media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
            assert media is not None
            season = SeasonRepository(session).upsert(
                media.id,
                season_number,
                tmdb_season_id=detail.id,
                name=detail.name,
                overview=detail.overview,
                poster_path=detail.poster_path,
                air_date=_date(detail.air_date),
                last_synced_at=utc_now(),
            )
            episodes = EpisodeRepository(session)
            for episode in detail.episodes:
                episodes.upsert(
                    season.id,
                    episode.episode_number,
                    tmdb_episode_id=episode.id,
                    name=episode.original_name or episode.name,
                    overview=episode.overview,
                    air_date=_date(episode.air_date),
                    runtime=episode.runtime,
                    still_path=episode.still_path,
                )
        return self.cached_season(tv_id, season_number) or []

    def season_needs_refresh(
        self,
        tv_id: int,
        season_number: int,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Check one season's episode metadata timestamp without network access."""
        with self._sessions()() as session:
            media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
            if media is None:
                return True
            season = next(
                (
                    item
                    for item in SeasonRepository(session).list_for_media(media.id)
                    if item.season_number == season_number
                ),
                None,
            )
            return season is None or not metadata_is_fresh(
                season.last_synced_at, now=now
            )

    def has_cached_season(self, tv_id: int, season_number: int) -> bool:
        """Return true only after one successful full season sync."""
        with self._sessions()() as session:
            media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
            if media is None:
                return False
            return any(
                season.season_number == season_number
                and season.last_synced_at is not None
                for season in SeasonRepository(session).list_for_media(media.id)
            )

    def cached_season(
        self, tv_id: int, season_number: int
    ) -> list[dict[str, Any]] | None:
        with self._sessions()() as session:
            media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
            if media is None:
                return None
            season = next(
                (
                    item
                    for item in SeasonRepository(session).list_for_media(media.id)
                    if item.season_number == season_number
                ),
                None,
            )
            if season is None:
                return None
            repo = EpisodeRepository(session)
            result = []
            for episode, progress in repo.list_for_season_with_progress(season.id):
                result.append(
                    {
                        "number": episode.episode_number,
                        "name": episode.name or "",
                        "date": episode.air_date.isoformat()
                        if episode.air_date
                        else "",
                        "overview": episode.overview or "",
                        "stillPath": episode.still_path or "",
                        "still": "",
                        "watched": bool(progress and progress.watched),
                    }
                )
            return result

    def set_episode_watched(
        self, tv_id: int, season_number: int, episode_number: int, watched: bool,
        *, require_in_library: bool = False,
    ) -> list[dict[str, Any]]:
        """Change exactly one local episode progress row."""
        with self._sessions().begin() as session:
            if require_in_library:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
            if media is None:
                raise LookupError("Dizi bulunamadı")
            if require_in_library:
                user = UserMediaRepository(session).get(media.id)
                if user is None or user.status is None:
                    raise LookupError("Dizi kütüphanede değil")
            season = next(
                (
                    item
                    for item in SeasonRepository(session).list_for_media(media.id)
                    if item.season_number == season_number
                ),
                None,
            )
            if season is None:
                raise LookupError("Sezon bulunamadı")
            repo = EpisodeRepository(session)
            episode = next(
                (
                    item
                    for item in repo.list_for_season(season.id)
                    if item.episode_number == episode_number
                ),
                None,
            )
            if episode is None:
                raise LookupError("Bölüm bulunamadı")
            if require_in_library and (
                season_number <= 0 or episode.air_date is None
                or episode.air_date > date.today()
            ):
                raise ValueError("Devam Et yalnız yayınlanmış normal bölümler içindir")
            repo.set_watched(episode.id, watched)
            self._sync_status(session, media.id, explicit_unwatch=not watched)
        return self.cached_season(tv_id, season_number) or []

    def _ensure_complete(self, tv_id: int, numbers: list[int]) -> None:
        detail = self.cached(tv_id)
        if detail is None:
            raise LookupError("Dizi bulunamadı")
        expected = {
            season["number"]: season["episodeCount"] for season in detail["seasons"]
        }
        for number in numbers:
            current = self.cached_season(tv_id, number)
            if current is None or len(current) < expected[number]:
                self.load_season(tv_id, number)
                current = self.cached_season(tv_id, number)
            if current is None or len(current) < expected[number]:
                raise ValueError("Bölüm listesi eksik; toplu işlem yapılamadı.")

    def set_bulk_watched(
        self, tv_id: int, season_number: int | None, watched: bool
    ) -> list[dict[str, Any]]:
        """Atomically change every episode in a complete season or series."""
        detail = self.cached(tv_id)
        if detail is None:
            raise LookupError("Dizi bulunamadı")
        numbers = (
            [season["number"] for season in detail["seasons"]]
            if season_number is None
            else [season_number]
        )
        expected = {season["number"] for season in detail["seasons"]}
        if not set(numbers) <= expected:
            raise LookupError("Sezon bulunamadı")
        self._ensure_complete(tv_id, numbers)
        with self._sessions().begin() as session:
            media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
            assert media is not None
            repo = EpisodeRepository(session)
            for season in SeasonRepository(session).list_for_media(media.id):
                if season.season_number in numbers:
                    for episode in repo.list_for_season(season.id):
                        repo.set_watched(episode.id, watched)
            self._sync_status(session, media.id, explicit_unwatch=not watched)
        if season_number is None:
            return []
        return self.cached_season(tv_id, season_number) or []

    def set_status(self, tv_id: int, status: str | None) -> dict[str, Any]:
        """Set tracking status; None preserves episodes, favorites and lists."""
        selected = TrackingStatus(status) if status is not None else None
        with self._sessions().begin() as session:
            media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
            if media is None:
                raise LookupError("Dizi bulunamadı")
            UserMediaRepository(session).set_status(media.id, selected)
        return self.cached(tv_id) or {}

    def set_favorite(self, tv_id: int, favorite: bool) -> dict[str, Any]:
        with self._sessions().begin() as session:
            media = MediaRepository(session).get_by_tmdb(tv_id, MediaType.TV)
            if media is None:
                raise LookupError("Dizi bulunamadı")
            UserMediaRepository(session).set_favorite(media.id, favorite)
        return self.cached(tv_id) or {}

    def add_to_list(self, tv_id: int, name: str) -> dict[str, Any]:
        """Add this locally cached show to a named custom list."""
        CustomListsService(self._sessions()).add_by_name("tv", tv_id, name)
        return self.cached(tv_id) or {}
