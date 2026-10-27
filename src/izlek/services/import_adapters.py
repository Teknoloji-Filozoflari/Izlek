"""Convert Trakt JSON and Letterboxd CSV exports into İzlek transfer documents."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

from izlek.services.transfer_schema import SCHEMA_VERSION, IzlekExport

MediaKind = Literal["MOVIE", "TV"]
StatusKind = Literal["PLANNED", "WATCHING", "WATCHED"]

_STATUS_RANK = {"PLANNED": 1, "WATCHING": 2, "WATCHED": 3}


class ExternalImportError(ValueError):
    """A safe validation error while reading an external export."""


@dataclass(frozen=True)
class ExternalImport:
    """An İzlek document produced from a third-party export."""

    document: IzlekExport
    source: str
    skipped: int = 0


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        if "T" in text:
            parsed = datetime.fromisoformat(text)
        else:
            parsed = datetime.fromisoformat(f"{text}T00:00:00+00:00")
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_header(value: str) -> str:
    return "".join(ch for ch in value.casefold().strip() if ch.isalnum() or ch == "_")


def _tmdb_id(ids: Mapping[str, Any] | None) -> int | None:
    if not isinstance(ids, Mapping):
        return None
    raw = ids.get("tmdb")
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    try:
        parsed = int(str(raw).strip()) if raw is not None and str(raw).strip() else None
    except (TypeError, ValueError):
        return None
    return parsed if parsed is not None and parsed > 0 else None


def _title_of(payload: Mapping[str, Any] | None, fallback: str) -> str:
    if not isinstance(payload, Mapping):
        return fallback
    for key in ("title", "name", "original_title", "original_name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:500]
    return fallback


def _letterboxd_rating_to_10(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    try:
        rating = float(text.replace(",", "."))
    except ValueError:
        return None
    if "." not in text and "," not in text and 1 <= rating <= 10:
        return int(rating)
    if 0.5 <= rating <= 5:
        return max(1, min(10, int(round(rating * 2))))
    if 1 <= rating <= 10:
        return max(1, min(10, int(round(rating))))
    return None


def _trakt_rating(item: Mapping[str, Any]) -> int | None:
    rating = item.get("rating")
    if isinstance(rating, int) and 1 <= rating <= 10:
        return rating
    return None


class ExternalImportBuilder:
    """Accumulate portable media/tracking rows for one external import file."""

    def __init__(self, *, source: str) -> None:
        self.source = source
        self.skipped = 0
        self._now = _now()
        self._media: dict[tuple[MediaKind, int], dict[str, Any]] = {}
        self._tracking: dict[tuple[MediaKind, int], dict[str, Any]] = {}
        self._episodes: dict[tuple[int, int, int], dict[str, Any]] = {}
        self._lists: dict[str, dict[str, Any]] = {}

    def skip(self, count: int = 1) -> None:
        self.skipped += count

    def ensure_media(
        self,
        media_type: MediaKind,
        tmdb_id: int,
        title: str,
        *,
        release: date | None = None,
    ) -> dict[str, Any]:
        key = (media_type, tmdb_id)
        item = self._media.get(key)
        cleaned = title.strip()[:500] or f"TMDb {tmdb_id}"
        if item is None:
            item = {
                "tmdb_id": tmdb_id,
                "media_type": media_type,
                "original_title": cleaned,
                "original_language": None,
                "overview": None,
                "poster_path": None,
                "backdrop_path": None,
                "release_date": release if media_type == "MOVIE" else None,
                "first_air_date": release if media_type == "TV" else None,
                "runtime": None,
                "metadata": None,
                "last_synced_at": None,
                "created_at": self._now,
                "updated_at": self._now,
                "seasons": [],
            }
            self._media[key] = item
            return item
        if cleaned and item["original_title"].startswith("TMDb "):
            item["original_title"] = cleaned
        if release is not None:
            if media_type == "MOVIE" and item["release_date"] is None:
                item["release_date"] = release
            if media_type == "TV" and item["first_air_date"] is None:
                item["first_air_date"] = release
        return item

    def ensure_episode(
        self,
        show_tmdb_id: int,
        season_number: int,
        episode_number: int,
        *,
        title: str,
        show_title: str | None = None,
    ) -> None:
        media = self.ensure_media("TV", show_tmdb_id, show_title or title)
        seasons: list[dict[str, Any]] = media["seasons"]
        season = next(
            (item for item in seasons if item["season_number"] == season_number),
            None,
        )
        if season is None:
            season = {
                "season_number": season_number,
                "tmdb_season_id": None,
                "name": None,
                "overview": None,
                "poster_path": None,
                "air_date": None,
                "last_synced_at": None,
                "episodes": [],
            }
            seasons.append(season)
            seasons.sort(key=lambda item: item["season_number"])
        episodes: list[dict[str, Any]] = season["episodes"]
        if any(item["episode_number"] == episode_number for item in episodes):
            return
        episodes.append(
            {
                "episode_number": episode_number,
                "tmdb_episode_id": None,
                "name": title if title and not title.startswith("TMDb ") else None,
                "overview": None,
                "air_date": None,
                "runtime": None,
                "still_path": None,
            }
        )
        episodes.sort(key=lambda item: item["episode_number"])

    def set_status(
        self,
        media_type: MediaKind,
        tmdb_id: int,
        status: StatusKind | None,
        *,
        title: str,
        when: datetime | None = None,
        rating: int | None = None,
        note: str | None = None,
        release: date | None = None,
        manual: bool = True,
    ) -> None:
        self.ensure_media(media_type, tmdb_id, title, release=release)
        key = (media_type, tmdb_id)
        stamp = when or self._now
        current = self._tracking.get(key)
        if current is None:
            self._tracking[key] = {
                "tmdb_id": tmdb_id,
                "media_type": media_type,
                "status": status,
                "status_is_manual": manual and bool(status),
                "sort_order": None,
                "personal_rating": rating,
                "personal_note": note,
                "dismissed": None,
                "added_at": stamp,
                "updated_at": stamp,
            }
            return
        if status is not None:
            existing = current["status"]
            if existing is None or _STATUS_RANK[status] >= _STATUS_RANK[existing]:
                current["status"] = status
                current["status_is_manual"] = manual
        if rating is not None:
            current["personal_rating"] = rating
        if note is not None:
            current["personal_note"] = note
        current["added_at"] = min(current["added_at"], stamp)
        current["updated_at"] = max(current["updated_at"], stamp)

    def mark_watched_episode(
        self,
        show_tmdb_id: int,
        season_number: int,
        episode_number: int,
        *,
        show_title: str,
        episode_title: str | None = None,
        watched_at: datetime | None = None,
    ) -> None:
        self.ensure_episode(
            show_tmdb_id,
            season_number,
            episode_number,
            title=episode_title or f"S{season_number:02d}E{episode_number:02d}",
            show_title=show_title,
        )
        key = (show_tmdb_id, season_number, episode_number)
        stamp = watched_at
        current = self._episodes.get(key)
        if current is None:
            self._episodes[key] = {
                "tmdb_id": show_tmdb_id,
                "media_type": "TV",
                "season_number": season_number,
                "episode_number": episode_number,
                "watched": True,
                "watched_at": stamp,
            }
        elif stamp is not None and (
            current["watched_at"] is None or stamp > current["watched_at"]
        ):
            current["watched_at"] = stamp
        self.set_status(
            "TV",
            show_tmdb_id,
            "WATCHING",
            title=show_title,
            when=stamp,
        )

    def add_list_item(
        self,
        list_name: str,
        media_type: MediaKind,
        tmdb_id: int,
        *,
        title: str,
        when: datetime | None = None,
    ) -> None:
        self.ensure_media(media_type, tmdb_id, title)
        key = list_name.strip().casefold()
        if not key:
            return
        custom = self._lists.get(key)
        if custom is None:
            custom = {
                "name": list_name.strip()[:200],
                "sort_order": len(self._lists),
                "created_at": when or self._now,
                "items": [],
                "_keys": set(),
            }
            self._lists[key] = custom
        item_key = (media_type, tmdb_id)
        if item_key in custom["_keys"]:
            return
        custom["_keys"].add(item_key)
        custom["items"].append(
            {
                "tmdb_id": tmdb_id,
                "media_type": media_type,
                "sort_order": len(custom["items"]),
                "added_at": when or self._now,
            }
        )

    def finish(self) -> ExternalImport:
        if not self._media:
            raise ExternalImportError(
                "Dosyada TMDb kimliği olan içe aktarılabilir kayıt bulunamadı"
            )
        lists = []
        for custom in self._lists.values():
            payload = dict(custom)
            payload.pop("_keys", None)
            lists.append(payload)
        document = IzlekExport.model_validate(
            {
                "schema_version": SCHEMA_VERSION,
                "exported_at": self._now,
                "app_version": f"{self.source}-import",
                "media": list(self._media.values()),
                "tracking": list(self._tracking.values()),
                "episodes": list(self._episodes.values()),
                "favorites": [],
                "lists": lists,
            }
        )
        return ExternalImport(
            document=document, source=self.source, skipped=self.skipped
        )


def detect_trakt_payload(raw: Any) -> bool:
    """Return True when the JSON root looks like a Trakt export array."""
    if not isinstance(raw, list) or not raw:
        return False
    first = raw[0]
    if not isinstance(first, dict):
        return False
    if "movie" in first or "show" in first:
        return True
    return first.get("type") in {"movie", "show", "episode", "season"}


def trakt_to_export(raw: Sequence[Any]) -> ExternalImport:
    """Map Trakt watched/history/ratings/watchlist JSON arrays into İzlek JSON."""
    if not isinstance(raw, list):
        raise ExternalImportError("Trakt export kökü JSON dizi olmalı")
    builder = ExternalImportBuilder(source="trakt")
    for item in raw:
        if not isinstance(item, dict):
            builder.skip()
            continue
        if not _ingest_trakt_item(builder, item):
            builder.skip()
    return builder.finish()


def _year_release(payload: Mapping[str, Any]) -> date | None:
    year = payload.get("year")
    if isinstance(year, int) and year > 0:
        return date(year, 1, 1)
    return None


def _ingest_trakt_item(builder: ExternalImportBuilder, item: dict[str, Any]) -> bool:
    item_type = item.get("type")
    if item_type == "episode":
        return _ingest_trakt_episode(builder, item)
    movie_only = "movie" in item and item_type is None and "show" not in item
    if item_type == "movie" or movie_only:
        return _ingest_trakt_movie(builder, item)
    if item_type == "show" or "show" in item:
        return _ingest_trakt_show(builder, item)
    return False


def _ingest_trakt_movie(builder: ExternalImportBuilder, item: dict[str, Any]) -> bool:
    movie = item.get("movie")
    if not isinstance(movie, dict):
        return False
    tmdb_id = _tmdb_id(movie.get("ids"))
    if tmdb_id is None:
        return False
    title = _title_of(movie, f"TMDb {tmdb_id}")
    when = _parse_datetime(
        item.get("last_watched_at")
        or item.get("watched_at")
        or item.get("listed_at")
        or item.get("rated_at")
    )
    personal = _trakt_rating(item)
    if item.get("last_watched_at") or item.get("watched_at") or item.get("plays"):
        status: StatusKind = "WATCHED"
    elif item.get("listed_at"):
        status = "PLANNED"
    elif personal is not None:
        status = "WATCHED"
    else:
        status = "PLANNED"
    builder.set_status(
        "MOVIE",
        tmdb_id,
        status,
        title=title,
        when=when,
        rating=personal,
        release=_year_release(movie),
    )
    return True


def _ingest_trakt_episode(builder: ExternalImportBuilder, item: dict[str, Any]) -> bool:
    show = item.get("show")
    episode = item.get("episode")
    if not isinstance(show, dict) or not isinstance(episode, dict):
        return False
    show_id = _tmdb_id(show.get("ids"))
    if show_id is None:
        return False
    season_number = episode.get("season")
    episode_number = episode.get("number")
    if not isinstance(season_number, int) or not isinstance(episode_number, int):
        return False
    builder.mark_watched_episode(
        show_id,
        season_number,
        episode_number,
        show_title=_title_of(show, f"TMDb {show_id}"),
        episode_title=_title_of(episode, ""),
        watched_at=_parse_datetime(item.get("watched_at")),
    )
    return True


def _ingest_trakt_show(builder: ExternalImportBuilder, item: dict[str, Any]) -> bool:
    show = item.get("show")
    if not isinstance(show, dict):
        return False
    show_id = _tmdb_id(show.get("ids"))
    if show_id is None:
        return False
    title = _title_of(show, f"TMDb {show_id}")
    when = _parse_datetime(
        item.get("last_watched_at")
        or item.get("watched_at")
        or item.get("listed_at")
        or item.get("rated_at")
    )
    personal = _trakt_rating(item)
    seasons = item.get("seasons")
    watched_any = False
    if isinstance(seasons, list):
        for season in seasons:
            if not isinstance(season, dict):
                continue
            season_number = season.get("number")
            if not isinstance(season_number, int):
                continue
            for episode in season.get("episodes") or []:
                if not isinstance(episode, dict):
                    continue
                episode_number = episode.get("number")
                if not isinstance(episode_number, int):
                    continue
                watched_any = True
                builder.mark_watched_episode(
                    show_id,
                    season_number,
                    episode_number,
                    show_title=title,
                    watched_at=_parse_datetime(episode.get("last_watched_at")),
                )
    if watched_any:
        status: StatusKind = "WATCHING"
    elif item.get("listed_at"):
        status = "PLANNED"
    elif personal is not None:
        status = "WATCHED"
    else:
        status = "WATCHING"
    builder.set_status(
        "TV",
        show_id,
        status,
        title=title,
        when=when,
        rating=personal,
        release=_year_release(show),
    )
    return True


def letterboxd_to_export(path: Path, content: bytes | None = None) -> ExternalImport:
    """Map a Letterboxd CSV (export or import format) into İzlek JSON."""
    try:
        raw = content if content is not None else path.read_bytes()
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise ExternalImportError("Letterboxd CSV okunamadı") from exc
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if reader.fieldnames is None:
        raise ExternalImportError("Letterboxd CSV başlık satırı eksik")
    headers = {_normalize_header(name): name for name in reader.fieldnames if name}
    tmdb_header = next(
        (headers[key] for key in ("tmdbid", "tmdb_id", "tmdb") if key in headers),
        None,
    )
    if tmdb_header is None:
        raise ExternalImportError(
            "Letterboxd CSV içinde tmdbID / tmdb_id sütunu gerekli "
            "(çevrimdışı eşleştirme için)"
        )
    title_header = next(
        (headers[key] for key in ("name", "title", "film") if key in headers),
        None,
    )
    year_header = headers.get("year")
    rating_header = next(
        (
            headers[key]
            for key in ("rating10", "rating", "yourrating")
            if key in headers
        ),
        None,
    )
    watched_header = next(
        (
            headers[key]
            for key in ("watcheddate", "watched_date", "date")
            if key in headers
        ),
        None,
    )
    review_header = next(
        (headers[key] for key in ("review", "notes", "note") if key in headers),
        None,
    )
    list_header = headers.get("list")
    watchlist_hint = "watchlist" in path.name.casefold()

    builder = ExternalImportBuilder(source="letterboxd")
    for row in reader:
        raw_id = (row.get(tmdb_header) or "").strip()
        try:
            tmdb_id = int(raw_id)
        except ValueError:
            builder.skip()
            continue
        if tmdb_id <= 0:
            builder.skip()
            continue
        title = (row.get(title_header) or "").strip() if title_header else ""
        title = title or f"TMDb {tmdb_id}"
        release = None
        if year_header:
            year_text = (row.get(year_header) or "").strip()
            if year_text.isdigit() and int(year_text) > 0:
                release = date(int(year_text), 1, 1)
        rating = (
            _letterboxd_rating_to_10(row.get(rating_header) or "")
            if rating_header
            else None
        )
        when = _parse_datetime(row.get(watched_header)) if watched_header else None
        note = None
        if review_header:
            note_text = (row.get(review_header) or "").strip()
            if note_text:
                note = note_text[:2000]
        watched_value = ""
        if watched_header:
            watched_value = (row.get(watched_header) or "").strip()
        if watchlist_hint and not watched_value:
            status: StatusKind = "PLANNED"
        else:
            status = "WATCHED"
        builder.set_status(
            "MOVIE",
            tmdb_id,
            status,
            title=title,
            when=when,
            rating=rating,
            note=note,
            release=release,
        )
        if list_header:
            list_name = (row.get(list_header) or "").strip()
            if list_name:
                builder.add_list_item(
                    list_name, "MOVIE", tmdb_id, title=title, when=when
                )
    return builder.finish()


def load_json_payload(content: bytes) -> Any:
    try:
        return json.loads(content)
    except (json.JSONDecodeError, RecursionError, UnicodeError) as exc:
        raise ExternalImportError("Dosya geçerli JSON değil") from exc
