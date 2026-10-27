"""Local user tags for media; independent of custom-list membership."""

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType
from izlek.repositories.local import MediaRepository, TagRepository


def _clean_name(name: str) -> str:
    name = " ".join(name.split())
    if not name or len(name) > 80:
        raise ValueError("Etiket adı 1–80 karakter olmalı")
    return name


class TagsService:
    """Persist tag definitions and media attachments in SQLite."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._factory = session_factory
        self._owned_engine: Engine | None = None

    def _sessions(self) -> sessionmaker[Session]:
        if self._factory is None:
            self._owned_engine = initialize_database()
            self._factory = create_session_factory(self._owned_engine)
        return self._factory

    def list_all(self) -> list[dict]:
        with self._sessions()() as session:
            repo = TagRepository(session)
            counts = repo.counts()
            return [
                {"id": item.id, "name": item.name, "count": counts.get(item.id, 0)}
                for item in repo.list_all()
            ]

    def names_for(self, kind: str, tmdb_id: int) -> list[str]:
        with self._sessions()() as session:
            media = MediaRepository(session).get_by_tmdb(
                tmdb_id, MediaType(kind.upper())
            )
            if media is None:
                return []
            return TagRepository(session).names_for_media(media.id)

    def create(self, name: str) -> int:
        name = _clean_name(name)
        with self._sessions().begin() as session:
            repo = TagRepository(session)
            if any(item.name.casefold() == name.casefold() for item in repo.list_all()):
                raise ValueError("Bu adla bir etiket zaten var")
            return repo.create(name).id

    def rename(self, tag_id: int, name: str) -> None:
        name = _clean_name(name)
        with self._sessions().begin() as session:
            repo = TagRepository(session)
            if any(
                item.id != tag_id and item.name.casefold() == name.casefold()
                for item in repo.list_all()
            ):
                raise ValueError("Bu adla bir etiket zaten var")
            repo.rename(tag_id, name)

    def delete(self, tag_id: int) -> None:
        with self._sessions().begin() as session:
            if not TagRepository(session).delete(tag_id):
                raise LookupError("Etiket bulunamadı")

    def set_for_media(self, kind: str, tmdb_id: int, names: list[str]) -> list[str]:
        """Replace a media item's tags; creates missing tag names as needed."""
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in names:
            name = _clean_name(str(raw))
            key = name.casefold()
            if key not in seen:
                cleaned.append(name)
                seen.add(key)
        if len(cleaned) > 20:
            raise ValueError("Bir içeriğe en fazla 20 etiket eklenebilir")
        with self._sessions().begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            media = MediaRepository(session).get_by_tmdb(
                tmdb_id, MediaType(kind.upper())
            )
            if media is None:
                raise LookupError("İçerik henüz yüklenmedi. Tekrar deneyin.")
            repo = TagRepository(session)
            by_fold = {item.name.casefold(): item for item in repo.list_all()}
            tag_ids: list[int] = []
            for name in cleaned:
                existing = by_fold.get(name.casefold())
                if existing is None:
                    existing = repo.create(name)
                    by_fold[name.casefold()] = existing
                tag_ids.append(existing.id)
            repo.set_for_media(media.id, tag_ids)
            return repo.names_for_media(media.id)

    def add_to_media(self, kind: str, tmdb_id: int, name: str) -> list[str]:
        name = _clean_name(name)
        current = self.names_for(kind, tmdb_id)
        if name.casefold() not in {item.casefold() for item in current}:
            current.append(name)
        return self.set_for_media(kind, tmdb_id, current)

    def remove_from_media(self, kind: str, tmdb_id: int, name: str) -> list[str]:
        name = _clean_name(name)
        current = [
            item for item in self.names_for(kind, tmdb_id)
            if item.casefold() != name.casefold()
        ]
        return self.set_for_media(kind, tmdb_id, current)

    def close(self) -> None:
        if self._owned_engine is not None:
            self._owned_engine.dispose()
