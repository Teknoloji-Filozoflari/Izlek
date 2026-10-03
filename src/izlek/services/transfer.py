"""Versioned, full-fidelity local JSON import and export."""

import json
import os
import tempfile
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import (
    CustomListRepository,
    EpisodeRepository,
    MediaRepository,
    SeasonRepository,
    TransferRepository,
    UserMediaRepository,
)
from izlek.services.transfer_schema import SCHEMA_VERSION, IzlekExport

_MAX_IMPORT_BYTES = 64 * 1024 * 1024
_SCHEMA_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}
_BLOCKED_METADATA_KEYS = {
    "access_token",
    "authorization",
    "cache_path",
    "cachepath",
    "local_path",
    "localpath",
    "backdrop",
    "poster",
    "still",
    "token",
}


class TransferError(ValueError):
    """A safe validation or file-format error for the import UI."""


def _app_version() -> str:
    try:
        return version("izlek")
    except PackageNotFoundError:
        return "1.0.0"


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _clean_metadata(value: Any) -> Any:
    """Drop secret/local-path keys while retaining portable TMDb JSON."""
    if isinstance(value, dict):
        return {
            str(key): _clean_metadata(item)
            for key, item in value.items()
            if str(key).casefold() not in _BLOCKED_METADATA_KEYS
        }
    if isinstance(value, list):
        return [_clean_metadata(item) for item in value]
    return value


def _migrate_schema(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply sequential migrations before validating the current schema."""
    raw_version = payload.get("schema_version")
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        raise TransferError("schema_version eksik veya geçersiz")
    if raw_version > SCHEMA_VERSION:
        raise TransferError(
            f"Bu dosya daha yeni bir İzlek şeması kullanıyor: {raw_version}"
        )
    migrated = dict(payload)
    while raw_version < SCHEMA_VERSION:
        migration = _SCHEMA_MIGRATIONS.get(raw_version)
        if migration is None:
            raise TransferError(
                f"Şema {raw_version} için import migration'ı bulunamadı"
            )
        migrated = migration(migrated)
        raw_version += 1
        migrated["schema_version"] = raw_version
    return migrated


def _prefer_imported(
    imported_at: datetime | None, local_at: datetime | None
) -> bool:
    imported = _naive(imported_at)
    local = _naive(local_at)
    if local is None:
        return True
    return imported is not None and imported >= local


class TransferService:
    """Export and merge portable user data using one local transaction."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._factory = session_factory
        self._owned_engine: Engine | None = None

    def _sessions(self) -> sessionmaker[Session]:
        if self._factory is None:
            self._owned_engine = initialize_database()
            self._factory = create_session_factory(self._owned_engine)
        return self._factory

    def build_export(self, *, exported_at: datetime | None = None) -> IzlekExport:
        """Build one portable document without tokens or image-cache paths."""
        with self._sessions()() as session:
            records = TransferRepository(session)
            media_rows = records.media()
            tracking_rows = records.tracking()
            season_rows = records.seasons()
            episode_rows = records.episodes()
            progress_rows = records.episode_progress()
            list_rows = records.lists()
            list_item_rows = records.list_items()

            media_by_id = {item.id: item for item in media_rows}
            seasons_by_id = {item.id: item for item in season_rows}
            episodes_by_id = {item.id: item for item in episode_rows}
            episodes_by_season: dict[int, list] = defaultdict(list)
            seasons_by_media: dict[int, list] = defaultdict(list)
            for season in season_rows:
                seasons_by_media[season.media_id].append(season)
            for episode in episode_rows:
                episodes_by_season[episode.season_id].append(episode)

            media = []
            for item in media_rows:
                seasons = []
                for season in seasons_by_media[item.id]:
                    seasons.append(
                        {
                            "season_number": season.season_number,
                            "tmdb_season_id": season.tmdb_season_id,
                            "name": season.name,
                            "overview": season.overview,
                            "poster_path": season.poster_path,
                            "air_date": season.air_date,
                            "last_synced_at": _aware(season.last_synced_at),
                            "episodes": [
                                {
                                    "episode_number": episode.episode_number,
                                    "tmdb_episode_id": episode.tmdb_episode_id,
                                    "name": episode.name,
                                    "overview": episode.overview,
                                    "air_date": episode.air_date,
                                    "runtime": episode.runtime,
                                    "still_path": episode.still_path,
                                }
                                for episode in episodes_by_season[season.id]
                            ],
                        }
                    )
                media.append(
                    {
                        "tmdb_id": item.tmdb_id,
                        "media_type": item.media_type.value,
                        "original_title": item.original_title,
                        "original_language": item.original_language,
                        "overview": item.overview,
                        "poster_path": item.poster_path,
                        "backdrop_path": item.backdrop_path,
                        "release_date": item.release_date,
                        "first_air_date": item.first_air_date,
                        "runtime": item.runtime,
                        "metadata": _clean_metadata(item.metadata_json),
                        "last_synced_at": _aware(item.last_synced_at),
                        "created_at": _aware(item.created_at),
                        "updated_at": _aware(item.updated_at),
                        "seasons": seasons,
                    }
                )

            tracking = []
            favorites = []
            for state in tracking_rows:
                item = media_by_id[state.media_id]
                identity = {
                    "tmdb_id": item.tmdb_id,
                    "media_type": item.media_type.value,
                }
                tracking.append(
                    {
                        **identity,
                        "status": state.status.value if state.status else None,
                        "status_is_manual": state.status_is_manual,
                        "added_at": _aware(state.added_at),
                        "updated_at": _aware(state.updated_at),
                    }
                )
                if state.favorite:
                    favorites.append(identity)

            progress = []
            for state in progress_rows:
                episode = episodes_by_id[state.episode_id]
                season = seasons_by_id[episode.season_id]
                item = media_by_id[season.media_id]
                progress.append(
                    {
                        "tmdb_id": item.tmdb_id,
                        "media_type": "TV",
                        "season_number": season.season_number,
                        "episode_number": episode.episode_number,
                        "watched": state.watched,
                        "watched_at": _aware(state.watched_at),
                    }
                )

            items_by_list: dict[int, list] = defaultdict(list)
            for member in list_item_rows:
                item = media_by_id[member.media_id]
                items_by_list[member.list_id].append(
                    {
                        "tmdb_id": item.tmdb_id,
                        "media_type": item.media_type.value,
                        "sort_order": member.sort_order,
                        "added_at": _aware(member.added_at),
                    }
                )
            lists = [
                {
                    "name": custom_list.name,
                    "sort_order": custom_list.sort_order,
                    "created_at": _aware(custom_list.created_at),
                    "items": items_by_list[custom_list.id],
                }
                for custom_list in list_rows
            ]

        return IzlekExport.model_validate(
            {
                "schema_version": SCHEMA_VERSION,
                "exported_at": _aware(exported_at or datetime.now(UTC)),
                "app_version": _app_version(),
                "media": media,
                "tracking": tracking,
                "episodes": progress,
                "favorites": favorites,
                "lists": lists,
            }
        )

    def export_file(self, path: Path) -> dict[str, int | str]:
        document = self.build_export()
        target = path.with_suffix(".json") if not path.suffix else path
        target.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(
            document.model_dump(mode="json"), ensure_ascii=False, indent=2
        ) + "\n"
        temporary: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(
                prefix=f".{target.name}.", dir=target.parent
            )
            temporary = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(0o600)
            os.replace(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return {**self.summary(document), "bytes": len(content.encode("utf-8"))}

    def read_file(self, path: Path) -> IzlekExport:
        try:
            if path.stat().st_size > _MAX_IMPORT_BYTES:
                raise TransferError("Import dosyası 64 MiB sınırını aşıyor")
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise TransferError("Import dosyası bulunamadı") from None
        except (OSError, UnicodeError):
            raise TransferError("Import dosyası okunamadı") from None
        except json.JSONDecodeError:
            raise TransferError("Dosya geçerli JSON değil") from None
        if not isinstance(raw, dict):
            raise TransferError("İzlek export kökü JSON object olmalı")
        try:
            return IzlekExport.model_validate(_migrate_schema(raw))
        except ValidationError as exc:
            first = exc.errors(include_url=False)[0]
            location = ".".join(str(part) for part in first["loc"])
            raise TransferError(
                f"Şema doğrulanamadı: {location or 'root'} — {first['msg']}"
            ) from None

    @staticmethod
    def summary(document: IzlekExport) -> dict[str, int | str]:
        media_keys = {(item.media_type, item.tmdb_id) for item in document.media}
        list_names = {item.name.casefold() for item in document.lists}
        return {
            "schema_version": document.schema_version,
            "app_version": document.app_version,
            "media": len(media_keys),
            "movies": sum(kind == "MOVIE" for kind, _ in media_keys),
            "shows": sum(kind == "TV" for kind, _ in media_keys),
            "tracking": len(document.tracking),
            "episode_progress": len(document.episodes),
            "favorites": len(document.favorites),
            "lists": len(list_names),
            "list_items": sum(len(item.items) for item in document.lists),
            "duplicate_media": len(document.media) - len(media_keys),
            "duplicate_lists": len(document.lists) - len(list_names),
        }

    def preview_file(self, path: Path) -> dict[str, int | str]:
        return self.summary(self.read_file(path))

    def import_file(self, path: Path) -> dict[str, int]:
        document = self.read_file(path)
        report = {
            "media_created": 0,
            "media_merged": 0,
            "tracking_merged": 0,
            "episode_progress_merged": 0,
            "lists_created": 0,
            "lists_merged": 0,
            "list_items_added": 0,
            "list_items_existing": 0,
        }
        with self._sessions().begin() as session:
            self._import_document(session, document, report)
        return report

    def _import_document(
        self, session: Session, document: IzlekExport, report: dict[str, int]
    ) -> None:
        media_repo = MediaRepository(session)
        season_repo = SeasonRepository(session)
        episode_repo = EpisodeRepository(session)
        user_repo = UserMediaRepository(session)
        list_repo = CustomListRepository(session)
        media_by_key = {}
        episode_by_key = {}

        for record in document.media:
            media_type = MediaType(record.media_type)
            existing = media_repo.get_by_tmdb(record.tmdb_id, media_type)
            if existing is None or _prefer_imported(
                record.last_synced_at, existing.last_synced_at
            ):
                item = media_repo.upsert(
                    record.tmdb_id,
                    media_type,
                    record.original_title,
                    original_language=record.original_language,
                    overview=record.overview,
                    poster_path=record.poster_path,
                    backdrop_path=record.backdrop_path,
                    release_date=record.release_date,
                    first_air_date=record.first_air_date,
                    runtime=record.runtime,
                    metadata_json=_clean_metadata(record.metadata),
                    last_synced_at=_naive(record.last_synced_at),
                )
            else:
                item = existing
            if existing is None:
                report["media_created"] += 1
                item.created_at = _naive(record.created_at) or item.created_at
                item.updated_at = _naive(record.updated_at) or item.updated_at
            else:
                report["media_merged"] += 1
                imported_created = _naive(record.created_at)
                if imported_created is not None:
                    item.created_at = min(item.created_at, imported_created)
                imported_updated = _naive(record.updated_at)
                if imported_updated is not None:
                    item.updated_at = max(item.updated_at, imported_updated)
            media_by_key[(record.media_type, record.tmdb_id)] = item

            for season_data in record.seasons:
                local_season = next(
                    (
                        season
                        for season in season_repo.list_for_media(item.id)
                        if season.season_number == season_data.season_number
                    ),
                    None,
                )
                if local_season is None or _prefer_imported(
                    season_data.last_synced_at, local_season.last_synced_at
                ):
                    season = season_repo.upsert(
                        item.id,
                        season_data.season_number,
                        tmdb_season_id=season_data.tmdb_season_id,
                        name=season_data.name,
                        overview=season_data.overview,
                        poster_path=season_data.poster_path,
                        air_date=season_data.air_date,
                        last_synced_at=_naive(season_data.last_synced_at),
                    )
                else:
                    season = local_season
                for episode_data in season_data.episodes:
                    local_episode = next(
                        (
                            episode
                            for episode in episode_repo.list_for_season(season.id)
                            if episode.episode_number
                            == episode_data.episode_number
                        ),
                        None,
                    )
                    episode = episode_repo.upsert(
                        season.id,
                        episode_data.episode_number,
                        tmdb_episode_id=episode_data.tmdb_episode_id
                        if episode_data.tmdb_episode_id is not None
                        else getattr(local_episode, "tmdb_episode_id", None),
                        name=episode_data.name
                        if episode_data.name is not None
                        else getattr(local_episode, "name", None),
                        overview=episode_data.overview
                        if episode_data.overview is not None
                        else getattr(local_episode, "overview", None),
                        air_date=episode_data.air_date
                        if episode_data.air_date is not None
                        else getattr(local_episode, "air_date", None),
                        runtime=episode_data.runtime
                        if episode_data.runtime is not None
                        else getattr(local_episode, "runtime", None),
                        still_path=episode_data.still_path
                        if episode_data.still_path is not None
                        else getattr(local_episode, "still_path", None),
                    )
                    episode_by_key[
                        (
                            record.tmdb_id,
                            season_data.season_number,
                            episode_data.episode_number,
                        )
                    ] = episode

        applied_tracking: set[tuple[str, int]] = set()
        for record in document.tracking:
            media = media_by_key[(record.media_type, record.tmdb_id)]
            state = user_repo.get(media.id)
            missing_state = state is None
            if state is None:
                state = user_repo.set_favorite(media.id, False)
            if missing_state or _prefer_imported(record.updated_at, state.updated_at):
                state.status = TrackingStatus(record.status) if record.status else None
                state.status_is_manual = record.status_is_manual and bool(record.status)
                state.added_at = min(
                    state.added_at, _naive(record.added_at) or state.added_at
                )
                state.updated_at = _naive(record.updated_at) or state.updated_at
                applied_tracking.add((record.media_type, record.tmdb_id))
            report["tracking_merged"] += 1

        for record in document.favorites:
            media = media_by_key[(record.media_type, record.tmdb_id)]
            user_repo.set_favorite(media.id, True)

        for record in document.tracking:
            key = (record.media_type, record.tmdb_id)
            if key not in applied_tracking:
                continue
            media = media_by_key[key]
            state = user_repo.get(media.id)
            assert state is not None
            state.added_at = _naive(record.added_at) or state.added_at
            state.updated_at = _naive(record.updated_at) or state.updated_at

        for record in document.episodes:
            episode = episode_by_key[
                (record.tmdb_id, record.season_number, record.episode_number)
            ]
            progress = episode_repo.get_progress(episode.id)
            if progress is None:
                progress = episode_repo.set_watched(episode.id, record.watched)
                progress.watched_at = _naive(record.watched_at)
            elif record.watched and not progress.watched:
                progress = episode_repo.set_watched(episode.id, True)
                progress.watched_at = _naive(record.watched_at)
            elif record.watched and record.watched_at is not None:
                imported_at = _naive(record.watched_at)
                if progress.watched_at is None or (
                    imported_at is not None and imported_at > progress.watched_at
                ):
                    progress.watched_at = imported_at
            report["episode_progress_merged"] += 1

        lists_by_name = {
            custom_list.name.casefold(): custom_list
            for custom_list in list_repo.list_all()
        }
        for record in document.lists:
            key = record.name.casefold()
            custom_list = lists_by_name.get(key)
            if custom_list is None:
                custom_list = list_repo.create(record.name, record.sort_order)
                custom_list.created_at = (
                    _naive(record.created_at) or custom_list.created_at
                )
                lists_by_name[key] = custom_list
                report["lists_created"] += 1
            else:
                report["lists_merged"] += 1
            existing_members = {
                member.media_id: member
                for member in list_repo.list_items(custom_list.id)
            }
            for member_data in record.items:
                media = media_by_key[(member_data.media_type, member_data.tmdb_id)]
                if media.id in existing_members:
                    report["list_items_existing"] += 1
                    continue
                member = list_repo.add_item(
                    custom_list.id, media.id, member_data.sort_order
                )
                member.added_at = _naive(member_data.added_at) or member.added_at
                existing_members[media.id] = member
                report["list_items_added"] += 1

        session.flush()

    def close(self) -> None:
        if self._owned_engine is not None:
            self._owned_engine.dispose()
