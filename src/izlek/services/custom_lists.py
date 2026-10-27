"""Local custom list management; no TMDb list endpoints are used."""

from datetime import date
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import (
    CustomListRepository,
    MediaRepository,
    TagRepository,
)
from izlek.services.smart_lists import (
    BUILTIN_SMART_LISTS,
    builtin_by_id,
    is_smart_list_id,
    tag_id_from_list,
    tag_list_id,
)


def _clean_name(name: str) -> str:
    name = name.strip()
    if not name or len(name) > 200:
        raise ValueError("Liste adı 1–200 karakter olmalı")
    return name


class CustomListsService:
    """Persist ordered lists and memberships in the local SQLite database."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._factory = session_factory
        self._owned_engine: Engine | None = None

    def _sessions(self) -> sessionmaker[Session]:
        if self._factory is None:
            self._owned_engine = initialize_database()
            self._factory = create_session_factory(self._owned_engine)
        return self._factory

    def snapshot(self, selected_id: int = 0) -> dict:
        """Return smart + custom list summaries, selected members, and candidates."""
        with self._sessions()() as session:
            repo = CustomListRepository(session)
            lists = repo.list_all()
            members_by_list = {item.id: [] for item in lists}
            for member in repo.list_all_items():
                members_by_list.setdefault(member.list_id, []).append(member)
            media_repo = MediaRepository(session)
            media_with_tracking = media_repo.list_all_with_tracking()
            all_media = [media for media, _ in media_with_tracking]
            media_by_id = {media.id: media for media in all_media}
            states = {
                media.id: user for media, user in media_with_tracking
                if user is not None
            }
            tag_repo = TagRepository(session)
            tags = tag_repo.list_all()
            tag_counts = tag_repo.counts()
            media_tags = tag_repo.names_by_media()
            smart_summaries = []
            for definition in BUILTIN_SMART_LISTS:
                matched = [
                    media for media, user in media_with_tracking
                    if definition.match(media, user)
                ]
                smart_summaries.append({
                    "id": definition.id,
                    "name": definition.name,
                    "count": len(matched),
                    "smart": True,
                    "key": definition.key,
                    "description": definition.description,
                })
            for tag in tags:
                smart_summaries.append({
                    "id": tag_list_id(tag.id),
                    "name": f"Etiket: {tag.name}",
                    "count": tag_counts.get(tag.id, 0),
                    "smart": True,
                    "key": f"tag:{tag.id}",
                    "description": f"«{tag.name}» etiketli içerikler",
                })
            custom_summaries = [
                {
                    "id": item.id,
                    "name": item.name,
                    "count": len(members_by_list[item.id]),
                    "smart": False,
                    "key": f"custom:{item.id}",
                    "description": "",
                }
                for item in lists
            ]
            summaries = smart_summaries + custom_summaries
            known_ids = {item["id"] for item in summaries}
            if selected_id not in known_ids:
                selected_id = summaries[0]["id"] if summaries else 0
            members = []
            selected_media_ids: set[int] = set()
            if is_smart_list_id(selected_id):
                tag_id = tag_id_from_list(selected_id)
                if tag_id is not None:
                    wanted = tag_repo.media_ids_for_tag(tag_id)
                    matched_media = [
                        media for media in all_media if media.id in wanted
                    ]
                else:
                    definition = builtin_by_id(selected_id)
                    matched_media = [
                        media for media, user in media_with_tracking
                        if definition and definition.match(media, user)
                    ]
                for media in matched_media:
                    selected_media_ids.add(media.id)
                    entry = self._media_dict(media, states.get(media.id))
                    entry["tags"] = media_tags.get(media.id, [])
                    members.append(entry)
                candidates = []
            else:
                for member in members_by_list.get(selected_id, []):
                    media = media_by_id.get(member.media_id)
                    if media is None:
                        continue
                    selected_media_ids.add(media.id)
                    entry = self._media_dict(media, states.get(media.id))
                    entry["tags"] = media_tags.get(media.id, [])
                    members.append(entry)
                candidates = [
                    self._media_dict(media)
                    for media in all_media
                    if media.id not in selected_media_ids
                ]
        return {
            "lists": summaries,
            "items": members,
            "candidates": candidates,
            "selected_id": selected_id,
        }

    @staticmethod
    def _require_custom(list_id: int) -> None:
        if is_smart_list_id(list_id):
            raise ValueError("Akıllı listeler düzenlenemez")

    @staticmethod
    def _media_dict(media, user=None) -> dict:
        status = user.status if user else None
        labels = {
            TrackingStatus.WATCHED: "İzlendi",
            TrackingStatus.WATCHING: "İzleniyor",
            TrackingStatus.PLANNED: "İzlenecek",
        }
        date = (
            media.release_date
            if media.media_type == MediaType.MOVIE
            else media.first_air_date
        )
        return {
            "tmdb_id": media.tmdb_id,
            "kind": media.media_type.value.lower(),
            "title": media.original_title,
            "display_title": media.original_title + " · " + (
                "Film" if media.media_type == MediaType.MOVIE else "Dizi"
            ),
            "poster_path": media.poster_path,
            "year": str(date.year) if date else "",
            "status": status.value if status else "",
            "status_label": labels.get(status, "İzlenmedi"),
            "watched": status == TrackingStatus.WATCHED,
        }

    def create(self, name: str) -> int:
        name = _clean_name(name)
        with self._sessions().begin() as session:
            repo = CustomListRepository(session)
            lists = repo.list_all()
            if any(item.name.casefold() == name.casefold() for item in lists):
                raise ValueError("Bu adla bir liste zaten var")
            return repo.create(name, len(lists)).id

    def rename(self, list_id: int, name: str) -> None:
        self._require_custom(list_id)
        name = _clean_name(name)
        with self._sessions().begin() as session:
            repo = CustomListRepository(session)
            if any(
                item.id != list_id and item.name.casefold() == name.casefold()
                for item in repo.list_all()
            ):
                raise ValueError("Bu adla bir liste zaten var")
            repo.rename(list_id, name)

    def delete(self, list_id: int) -> None:
        self._require_custom(list_id)
        with self._sessions().begin() as session:
            repo = CustomListRepository(session)
            if not repo.delete(list_id):
                raise LookupError("Liste bulunamadı")
            for position, item in enumerate(repo.list_all()):
                repo.set_position(item.id, position)

    def add(self, list_id: int, kind: str, tmdb_id: int) -> None:
        self._require_custom(list_id)
        media_type = MediaType(kind.upper())
        with self._sessions().begin() as session:
            repo = CustomListRepository(session)
            if repo.get(list_id) is None:
                raise LookupError("Liste bulunamadı")
            media = MediaRepository(session).get_by_tmdb(tmdb_id, media_type)
            if media is None:
                raise LookupError("Medya yerel veritabanında bulunamadı")
            members = repo.list_items(list_id)
            if not any(item.media_id == media.id for item in members):
                repo.add_item(list_id, media.id, len(members))

    def add_many(self, list_id: int, selections: list[dict]) -> None:
        """Validate every selection before atomically adding unique members."""
        self._require_custom(list_id)
        keys = list(dict.fromkeys(
            (MediaType(item["kind"].upper()), int(item["tmdb_id"]))
            for item in selections
        ))
        with self._sessions().begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            repo = CustomListRepository(session)
            if repo.get(list_id) is None:
                raise LookupError("Liste bulunamadı")
            media_repo = MediaRepository(session)
            selected = [media_repo.get_by_tmdb(item_id, kind) for kind, item_id in keys]
            if any(media is None for media in selected):
                raise LookupError("Seçilen içerik bulunamadı")
            members = repo.list_items(list_id)
            existing = {item.media_id for item in members}
            position = max((item.sort_order for item in members), default=-1) + 1
            for media in selected:
                if media.id not in existing:
                    repo.add_item(list_id, media.id, position)
                    existing.add(media.id)
                    position += 1

    def reorder_list(self, source: int, target: int) -> None:
        self._require_custom(source)
        self._require_custom(target)
        with self._sessions().begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            repo = CustomListRepository(session)
            items = repo.list_all()
            ids = [item.id for item in items]
            if source not in ids or target not in ids:
                raise LookupError("Liste bulunamadı")
            destination = ids.index(target)
            items.insert(destination, items.pop(ids.index(source)))
            for position, item in enumerate(items):
                repo.set_position(item.id, position)

    def reorder_item(
        self, list_id: int, source_kind: str, source_id: int,
        target_kind: str, target_id: int,
    ) -> None:
        self._require_custom(list_id)
        with self._sessions().begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            repo = CustomListRepository(session)
            media_repo = MediaRepository(session)
            source = media_repo.get_by_tmdb(source_id, MediaType(source_kind.upper()))
            target = media_repo.get_by_tmdb(target_id, MediaType(target_kind.upper()))
            members = repo.list_items(list_id)
            ids = [item.media_id for item in members]
            if (source is None or target is None
                    or source.id not in ids or target.id not in ids):
                raise LookupError("Liste içeriği bulunamadı")
            destination = ids.index(target.id)
            members.insert(destination, members.pop(ids.index(source.id)))
            for position, member in enumerate(members):
                repo.set_item_position(list_id, member.media_id, position)

    def add_by_name(self, kind: str, tmdb_id: int, name: str) -> int:
        """Choose a matching list or create one, then add a local media item."""
        name = _clean_name(name)
        with self._sessions().begin() as session:
            repo = CustomListRepository(session)
            media = MediaRepository(session).get_by_tmdb(
                tmdb_id, MediaType(kind.upper())
            )
            if media is None:
                raise LookupError("Medya yerel veritabanında bulunamadı")
            lists = repo.list_all()
            chosen = next(
                (item for item in lists if item.name.casefold() == name.casefold()),
                None,
            )
            if chosen is None:
                chosen = repo.create(name, len(lists))
            members = repo.list_items(chosen.id)
            if not any(item.media_id == media.id for item in members):
                repo.add_item(chosen.id, media.id, len(members))
            return chosen.id

    def add_collection_movies(
        self, name: str, movies: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Create or update a custom list from TMDb collection parts (list-only).

        Upserts local movie rows for membership without forcing tracking status,
        so users can still add/remove list items and library state separately.
        """
        name = _clean_name(name)
        cleaned: list[dict[str, Any]] = []
        for raw in movies:
            tmdb_id = int(raw.get("tmdb_id") or 0)
            title = str(raw.get("title") or "").strip()
            if tmdb_id <= 0 or not title:
                continue
            cleaned.append({
                "tmdb_id": tmdb_id,
                "title": title,
                "poster_path": raw.get("poster_path") or None,
                "overview": raw.get("overview") or None,
                "release_date": raw.get("release_date") or None,
            })
        if not cleaned:
            raise ValueError("Koleksiyonda eklenecek film yok")
        with self._sessions().begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            repo = CustomListRepository(session)
            media_repo = MediaRepository(session)
            lists = repo.list_all()
            chosen = next(
                (item for item in lists if item.name.casefold() == name.casefold()),
                None,
            )
            created = chosen is None
            if chosen is None:
                chosen = repo.create(name, len(lists))
            members = repo.list_items(chosen.id)
            existing = {item.media_id for item in members}
            position = max((item.sort_order for item in members), default=-1) + 1
            added = 0
            for movie in cleaned:
                media = media_repo.get_by_tmdb(movie["tmdb_id"], MediaType.MOVIE)
                release = None
                raw_date = movie.get("release_date") or ""
                if raw_date:
                    try:
                        release = date.fromisoformat(str(raw_date)[:10])
                    except ValueError:
                        release = None
                if media is None:
                    media = media_repo.upsert(
                        movie["tmdb_id"],
                        MediaType.MOVIE,
                        movie["title"],
                        poster_path=movie.get("poster_path"),
                        overview=movie.get("overview"),
                        release_date=release,
                    )
                else:
                    if not media.poster_path and movie.get("poster_path"):
                        media.poster_path = movie["poster_path"]
                    if release is not None and media.release_date is None:
                        media.release_date = release
                if media.id not in existing:
                    repo.add_item(chosen.id, media.id, position)
                    existing.add(media.id)
                    position += 1
                    added += 1
            return {
                "listId": chosen.id,
                "listName": chosen.name,
                "added": added,
                "total": len(cleaned),
                "already": len(cleaned) - added,
                "created": created,
            }

    def remove(self, list_id: int, kind: str, tmdb_id: int) -> None:
        self._require_custom(list_id)
        with self._sessions().begin() as session:
            repo = CustomListRepository(session)
            media = MediaRepository(session).get_by_tmdb(
                tmdb_id, MediaType(kind.upper())
            )
            if media is None or not repo.remove_item(list_id, media.id):
                raise LookupError("Liste öğesi bulunamadı")
            for position, item in enumerate(repo.list_items(list_id)):
                repo.set_item_position(list_id, item.media_id, position)

    def move_list(self, list_id: int, direction: int) -> None:
        self._require_custom(list_id)
        with self._sessions().begin() as session:
            repo = CustomListRepository(session)
            lists = repo.list_all()
            index = next((i for i, item in enumerate(lists) if item.id == list_id), -1)
            target = index + direction
            if index < 0 or target < 0 or target >= len(lists):
                return
            lists[index], lists[target] = lists[target], lists[index]
            for position, item in enumerate(lists):
                repo.set_position(item.id, position)

    def move_item(self, list_id: int, kind: str, tmdb_id: int, direction: int) -> None:
        self._require_custom(list_id)
        with self._sessions().begin() as session:
            repo = CustomListRepository(session)
            media = MediaRepository(session).get_by_tmdb(
                tmdb_id, MediaType(kind.upper())
            )
            if media is None:
                raise LookupError("Medya bulunamadı")
            members = repo.list_items(list_id)
            index = next(
                (i for i, item in enumerate(members) if item.media_id == media.id), -1
            )
            target = index + direction
            if index < 0 or target < 0 or target >= len(members):
                return
            members[index], members[target] = members[target], members[index]
            for position, item in enumerate(members):
                repo.set_item_position(list_id, item.media_id, position)

    def close(self) -> None:
        if self._owned_engine is not None:
            self._owned_engine.dispose()
