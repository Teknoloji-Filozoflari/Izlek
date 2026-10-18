"""Atomic user ordering of tracked film and TV cards."""

from sqlalchemy.orm import Session, sessionmaker

from izlek.db.models import MediaType
from izlek.repositories.local import MediaRepository


class LibraryOrderService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def move(
        self, kind: MediaType, source: int, target: int, displayed: list[int]
    ) -> None:
        """Move to the target's displayed position; preserve concurrent additions."""
        if source == target:
            return
        if len(displayed) != len(set(displayed)):
            raise ValueError("Yinelenen kart kimliği")
        with self._factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            rows = MediaRepository(session).list_local_media(kind)
            states = {media.tmdb_id: user for media, user in rows if user.status}
            if source not in states or target not in states:
                raise LookupError("Kart artık kütüphanede değil")
            order = [item_id for item_id in displayed if item_id in states]
            if source not in order or target not in order:
                raise ValueError("Kart sırası güncel değil")
            target_index = order.index(target)
            order.insert(target_index, order.pop(order.index(source)))
            remaining = sorted(
                states.keys() - set(order),
                key=lambda key: (
                    states[key].sort_order is None,
                    states[key].sort_order or 0,
                    -states[key].added_at.timestamp(),
                    -key,
                ),
            )
            for position, item_id in enumerate(order + remaining):
                states[item_id].sort_order = position
