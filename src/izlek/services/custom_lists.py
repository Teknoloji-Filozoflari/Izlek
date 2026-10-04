"""Local custom list management; no TMDb list endpoints are used."""

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType
from izlek.repositories.local import CustomListRepository, MediaRepository


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
            all_media = media_repo.list_all()
            media_by_id = {media.id: media for media in all_media}
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
                members.append(self._media_dict(media))
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
    def _media_dict(media) -> dict:
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
