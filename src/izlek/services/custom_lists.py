"""Local custom list management; no TMDb list endpoints are used."""

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import (
    CustomListRepository,
    MediaRepository,
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
        """Return list summaries, selected members, and locally known candidates."""
        with self._sessions()() as session:
            repo = CustomListRepository(session)
            lists = repo.list_all()
            if not any(item.id == selected_id for item in lists):
                selected_id = lists[0].id if lists else 0
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
            summaries = [
                {
                    "id": item.id,
                    "name": item.name,
                    "count": len(members_by_list[item.id]),
                }
                for item in lists
            ]
            members = []
            selected_media_ids = set()
            for member in members_by_list.get(selected_id, []):
                media = media_by_id.get(member.media_id)
                if media is None:
                    continue
                selected_media_ids.add(media.id)
                members.append(self._media_dict(media, states.get(media.id)))
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
        with self._sessions().begin() as session:
            repo = CustomListRepository(session)
            if not repo.delete(list_id):
                raise LookupError("Liste bulunamadı")
            for position, item in enumerate(repo.list_all()):
                repo.set_position(item.id, position)

    def add(self, list_id: int, kind: str, tmdb_id: int) -> None:
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

    def remove(self, list_id: int, kind: str, tmdb_id: int) -> None:
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
