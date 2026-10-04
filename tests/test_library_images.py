"""All tracked artwork is kept locally, independently of visible cards."""

import os
from datetime import UTC, datetime, timedelta

import httpx

from izlek.db.engine import create_session_factory, initialize_database
from izlek.db.models import MediaType, TrackingStatus
from izlek.repositories.local import MediaRepository, UserMediaRepository
from izlek.services.library_images import LibraryImagesService
from test_image_service import JPEG, FakeTmdb, make_service


def test_sync_downloads_all_tracked_artwork_and_keeps_it_offline(tmp_path):
    engine = initialize_database(tmp_path / "library.sqlite3")
    factory = create_session_factory(engine)
    with factory.begin() as session:
        repo = MediaRepository(session)
        for kind in (MediaType.MOVIE, MediaType.TV):
            media = repo.upsert(
                42, kind, kind.value, poster_path=f"/{kind.value}.jpg",
                backdrop_path=f"/{kind.value}-bg.jpg",
            )
            UserMediaRepository(session).set_status(media.id, TrackingStatus.PLANNED)
        repo.upsert(99, MediaType.MOVIE, "Not tracked", poster_path="/unused.jpg")
    requests = []

    def respond(request):
        requests.append(str(request.url))
        return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG)

    images, client = make_service(tmp_path, FakeTmdb(), respond)
    service = LibraryImagesService(factory, images=images)
    try:
        assert service.sync() == {"saved": 4, "unavailable": 0}
        assert len(requests) == 4
        expired = (datetime.now(UTC) - timedelta(days=200)).timestamp()
        for path in images.cache.root.glob("*.img"):
            os.utime(path, (expired, expired))
        assert images.cache.prune_expired() == 0
        assert images.cache.clear() == 0
        assert service.sync() == {"saved": 4, "unavailable": 0}
        assert len(requests) == 4
        assert images.poster("/MOVIE.jpg").result().read_bytes() == JPEG
    finally:
        service.close()
        images.close()
        client.close()
        engine.dispose()
