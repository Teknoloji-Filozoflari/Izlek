"""Local personal reviews, dismissal and atomic library batch operations."""

from threading import Lock

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import (
    CustomListRepository,
    MediaRepository,
    UserMediaRepository,
)


class PersonalMediaService:
    def __init__(self, factory: sessionmaker[Session] | None = None) -> None:
        self._factory = factory
        self._engine: Engine | None = None
        self._lock = Lock()

    def sessions(self) -> sessionmaker[Session]:
        with self._lock:
            if self._factory is None:
                self._engine = initialize_database()
                self._factory = create_session_factory(self._engine)
        return self._factory

    def read(self, kind: str, tmdb_id: int) -> dict:
        with self.sessions()() as session:
            media = MediaRepository(session).get_by_tmdb(
                tmdb_id, MediaType(kind.upper())
            )
            user = UserMediaRepository(session).get(media.id) if media else None
            return {
                "kind": kind,
                "id": tmdb_id,
                "rating": user.personal_rating or 0 if user else 0,
                "note": user.personal_note if user else "",
                "dismissed": bool(user and user.dismissed),
            }

    def save_review(self, kind: str, tmdb_id: int, rating: int, note: str) -> dict:
        if (
            isinstance(rating, bool)
            or not isinstance(rating, int)
            or not 0 <= rating <= 10
        ):
            raise ValueError("Puan 1–10 arasında olmalı; 0 puanı temizler.")
        if len(note) > 2000:
            raise ValueError("Not en fazla 2000 karakter olabilir.")
        with self.sessions().begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            media = MediaRepository(session).get_by_tmdb(
                tmdb_id, MediaType(kind.upper())
            )
            if media is None:
                raise LookupError("İçerik henüz yüklenmedi. Tekrar deneyin.")
            UserMediaRepository(session).set_personal(media.id, rating or None, note)
        return self.read(kind, tmdb_id)

    def dismiss(self, summary: dict, dismissed: bool) -> None:
        kind = MediaType(str(summary["mediaType"]).upper())
        tmdb_id = int(summary["id"])
        title = str(summary.get("title", "")).strip()
        if tmdb_id <= 0:
            raise ValueError("Geçersiz içerik")
        with self.sessions().begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            repo = MediaRepository(session)
            media = repo.get_by_tmdb(tmdb_id, kind)
            if media is None:
                if not dismissed or not title:
                    raise LookupError("İçerik bulunamadı")
                media = repo.upsert(
                    tmdb_id, kind, title, poster_path=summary.get("posterPath") or None
                )
            UserMediaRepository(session).set_dismissed(media.id, dismissed)

    def hidden(self) -> list[dict]:
        with self.sessions()() as session:
            return [
                {
                    "id": media.tmdb_id,
                    "mediaType": media.media_type.value.lower(),
                    "title": media.original_title,
                }
                for media, user in MediaRepository(session).list_all_with_tracking()
                if user and user.dismissed
            ]

    def suppressed_ids(self, kind: str) -> set[int]:
        with self.sessions()() as session:
            return MediaRepository(session).dismissed_tmdb_ids(MediaType(kind.upper()))

    def lists(self) -> list[dict]:
        with self.sessions()() as session:
            return [
                {"id": row.id, "name": row.name}
                for row in CustomListRepository(session).list_all()
            ]

    def batch(
        self, kind: str, tmdb_ids: list[int], action: str, list_id: int = 0
    ) -> int:
        """Validate the full selection and commit all members or none."""
        ids = list(dict.fromkeys(tmdb_ids))
        if not ids or action not in (
            "PLANNED",
            "WATCHING",
            "WATCHED",
            "favorite",
            "unfavorite",
            "list",
        ):
            raise ValueError("İçerik ve işlem seçin.")
        with self.sessions().begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            media_repo = MediaRepository(session)
            user_repo = UserMediaRepository(session)
            rows = [
                media_repo.get_by_tmdb(item_id, MediaType(kind.upper()))
                for item_id in ids
            ]
            if any(
                media is None
                or not (user_repo.get(media.id) and user_repo.get(media.id).status)
                for media in rows
            ):
                raise LookupError("Seçilen içeriklerden biri artık kütüphanede değil.")
            lists = CustomListRepository(session)
            if action == "list" and lists.get(list_id) is None:
                raise LookupError("Hedef liste bulunamadı.")
            members = lists.list_items(list_id) if action == "list" else []
            existing = {member.media_id for member in members}
            position = max((member.sort_order for member in members), default=-1) + 1
            for media in rows:
                if action in TrackingStatus._value2member_map_:
                    user_repo.set_status(media.id, TrackingStatus(action))
                elif action in ("favorite", "unfavorite"):
                    user_repo.set_favorite(media.id, action == "favorite")
                elif media.id not in existing:
                    lists.add_item(list_id, media.id, position)
                    position += 1
                    existing.add(media.id)
        return len(ids)

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
