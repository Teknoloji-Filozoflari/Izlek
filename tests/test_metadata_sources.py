"""Metadata client interface, settings, OMDb gate, and watch region."""

from pathlib import Path

import pytest

from izlek.metadata.capabilities import Capability
from izlek.metadata.catalog import (
    SOURCE_CATALOG,
    SourceId,
    normalize_watch_region,
)
from izlek.metadata.clients import OmdbMetadataClient, TmdbMetadataClient
from izlek.metadata.credentials import SourceCredentialStore
from izlek.metadata.protocol import UnsupportedCapabilityError
from izlek.metadata.registry import MetadataClientRegistry
from izlek.metadata.settings import MetadataSettings
from izlek.services.movie_detail import MovieDetailService
from izlek.tmdb.client import TmdbClient
from izlek.tmdb.models import MovieDetail, MovieWatchProviders
from izlek.ui.controllers.metadata_settings_controller import (
    MetadataSettingsController,
)


def test_catalog_matches_app_needs_and_keeps_tmdb_default():
    assert SOURCE_CATALOG[SourceId.TMDB].default_enabled is True
    assert Capability.DISCOVER in SOURCE_CATALOG[SourceId.TMDB].supported
    assert Capability.WATCH_PROVIDERS in SOURCE_CATALOG[SourceId.TMDB].supported
    assert Capability.TITLE_LOOKUP in SOURCE_CATALOG[SourceId.OMDB].supported
    assert Capability.DISCOVER not in SOURCE_CATALOG[SourceId.OMDB].supported
    assert Capability.WATCH_PROVIDERS not in SOURCE_CATALOG[SourceId.TRAKT].supported
    policy = SOURCE_CATALOG[SourceId.OMDB].commercial_policy.value
    assert policy == "non_commercial_only"


def test_metadata_settings_persist_region_and_capabilities(tmp_path: Path):
    path = tmp_path / "metadata-sources.json"
    settings = MetadataSettings(path)
    assert settings.watch_provider_region == "TR"
    assert settings.set_watch_provider_region("us") == "US"
    assert settings.set_watch_provider_region("zz") == "TR"

    settings.acknowledge_omdb_non_commercial(True)
    settings.set_source_enabled(SourceId.OMDB, True)
    settings.set_capability(SourceId.TRAKT, Capability.SEARCH, True)
    settings.set_source_enabled(SourceId.TRAKT, True)

    reloaded = MetadataSettings(path)
    assert reloaded.watch_provider_region == "TR"
    assert reloaded.is_enabled(SourceId.OMDB)
    assert Capability.TITLE_LOOKUP in reloaded.enabled_capabilities(SourceId.OMDB)
    assert reloaded.is_enabled(SourceId.TRAKT)
    assert Capability.SEARCH in reloaded.enabled_capabilities(SourceId.TRAKT)
    assert reloaded.is_enabled(SourceId.TMDB)


def test_omdb_requires_non_commercial_acknowledgment(tmp_path: Path):
    settings = MetadataSettings(tmp_path / "metadata-sources.json")
    with pytest.raises(ValueError, match="ticari olmayan"):
        settings.set_source_enabled(SourceId.OMDB, True)
    assert not settings.is_enabled(SourceId.OMDB)

    settings.acknowledge_omdb_non_commercial(True)
    settings.set_source_enabled(SourceId.OMDB, True)
    assert settings.is_enabled(SourceId.OMDB)

    settings.acknowledge_omdb_non_commercial(False)
    assert not settings.is_enabled(SourceId.OMDB)


def test_tmdb_cannot_be_disabled(tmp_path: Path):
    settings = MetadataSettings(tmp_path / "metadata-sources.json")
    settings.set_source_enabled(SourceId.TMDB, False)
    assert settings.is_enabled(SourceId.TMDB)


def test_registry_prefers_implemented_tmdb_and_exposes_matrix(tmp_path: Path):
    settings = MetadataSettings(tmp_path / "metadata-sources.json")
    registry = MetadataClientRegistry(settings, tmdb_client=TmdbClient(token="x"))
    client = registry.resolve(Capability.SEARCH)
    assert isinstance(client, TmdbMetadataClient)
    assert client.supports(Capability.SEARCH)

    matrix = registry.matrix()
    search = next(row for row in matrix if row["capability"] == "search")
    assert search["sources"]["tmdb"]["implemented"] is True
    assert search["sources"]["omdb"]["supported"] is False


def test_omdb_client_stays_gated_without_key_and_ack():
    client = OmdbMetadataClient(api_key=None, non_commercial_acknowledged=True)
    assert not client.supports(Capability.TITLE_LOOKUP)
    gated = OmdbMetadataClient(api_key="key", non_commercial_acknowledged=False)
    assert not gated.supports(Capability.TITLE_LOOKUP)
    ready = OmdbMetadataClient(api_key="key", non_commercial_acknowledged=True)
    assert ready.supports(Capability.TITLE_LOOKUP)
    with pytest.raises(UnsupportedCapabilityError):
        ready.title_lookup(title="Inception")


def test_source_credential_store_uses_secure_file_fallback(tmp_path: Path):
    store = SourceCredentialStore(
        SourceId.TRAKT,
        fallback_path=tmp_path / "trakt-credential",
        keyring_backend=None,
    )
    assert store.save("client-id-value") == "file"
    loaded = store.load()
    assert loaded is not None
    assert loaded.value == "client-id-value"
    assert loaded.location == "file"
    assert store.path.stat().st_mode & 0o077 == 0
    store.clear()
    assert store.load() is None


def test_movie_detail_uses_configured_watch_region(tmp_path):
    from izlek.db.engine import create_session_factory, initialize_database
    from izlek.db.models import MediaType
    from izlek.repositories.local import MediaRepository

    engine = initialize_database(tmp_path / "region.sqlite3")
    factory = create_session_factory(engine)
    service = MovieDetailService(
        TmdbClient(token="x"), factory, watch_region=lambda: "US"
    )
    providers = MovieWatchProviders.model_validate(
        {
            "id": 42,
            "results": {
                "TR": {
                    "link": "https://www.themoviedb.org/movie/42/watch?locale=TR",
                    "flatrate": [{"provider_id": 1, "provider_name": "TR Stream"}],
                },
                "US": {
                    "link": "https://www.themoviedb.org/movie/42/watch?locale=US",
                    "flatrate": [{"provider_id": 2, "provider_name": "US Stream"}],
                },
            },
        }
    )
    detail = MovieDetail.model_validate(
        {
            "id": 42,
            "title": "Test",
            "original_title": "Test",
            "overview": "",
            "poster_path": None,
            "backdrop_path": None,
            "release_date": "2020-01-01",
            "runtime": 100,
            "vote_average": 7.0,
            "genres": [],
        }
    )
    blob = {
        "detail": detail.model_dump(mode="json"),
        "providers": providers.model_dump(mode="json"),
    }
    with factory() as session:
        MediaRepository(session).upsert(
            42, MediaType.MOVIE, "Test", metadata_json=blob
        )
        session.commit()

    presented = service.cached(42)
    assert presented is not None
    assert presented["providers"]["Abonelik"] == ["US Stream"]
    assert presented["providerLink"].endswith("locale=US")
    engine.dispose()


def test_metadata_settings_controller_region_and_omdb_gate(tmp_path: Path):
    settings = MetadataSettings(tmp_path / "metadata-sources.json")
    controller = MetadataSettingsController(settings=settings)
    assert controller.watchProviderRegion == "TR"
    controller.setWatchProviderRegion("DE")
    assert controller.watchProviderRegion == "DE"
    assert any(item["code"] == "DE" for item in controller.watchProviderRegions)

    controller.setSourceEnabled("omdb", True)
    assert controller.feedbackKind == "danger"
    assert not settings.is_enabled(SourceId.OMDB)

    controller.acknowledgeOmdbNonCommercial(True)
    controller.setSourceEnabled("omdb", True)
    assert settings.is_enabled(SourceId.OMDB)
    sources = {item["id"]: item for item in controller.sources}
    assert sources["tmdb"]["isDefault"] is True
    assert sources["omdb"]["requiresNonCommercialAck"] is True
    assert sources["omdb"]["omdbNonCommercialAcknowledged"] is True


def test_normalize_watch_region_helpers():
    assert normalize_watch_region("tr") == "TR"
    assert normalize_watch_region("") == "TR"
    assert normalize_watch_region(None) == "TR"
