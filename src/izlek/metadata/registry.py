"""Resolve which configured metadata client should handle a capability."""

from __future__ import annotations

from collections.abc import Mapping

from izlek.metadata.capabilities import Capability
from izlek.metadata.catalog import SOURCE_CATALOG, SourceId
from izlek.metadata.clients import (
    BaseMetadataClient,
    TmdbMetadataClient,
    build_supplement_clients,
)
from izlek.metadata.credentials import SourceCredentialStore
from izlek.metadata.protocol import MetadataClient, UnsupportedCapabilityError
from izlek.metadata.settings import MetadataSettings
from izlek.security.token_store import TokenStore
from izlek.tmdb.client import TmdbClient

# Preference when multiple enabled sources claim the same capability.
_SOURCE_PRIORITY: tuple[SourceId, ...] = (
    SourceId.TMDB,
    SourceId.TRAKT,
    SourceId.TVMAZE,
    SourceId.OMDB,
)


class MetadataClientRegistry:
    """Settings-aware router; TMDb remains the runtime default for catalog work."""

    def __init__(
        self,
        settings: MetadataSettings | None = None,
        *,
        tmdb_client: TmdbClient | None = None,
        tmdb_store: TokenStore | None = None,
        clients: Mapping[SourceId, BaseMetadataClient] | None = None,
    ) -> None:
        self.settings = settings or MetadataSettings()
        self._tmdb_store = tmdb_store or TokenStore()
        if clients is not None:
            self._clients = dict(clients)
        else:
            token = None
            stored = self._tmdb_store.load()
            if stored is not None:
                token = stored.value
            tmdb = TmdbMetadataClient(tmdb_client or TmdbClient(token=token))
            supplements = self._load_supplements()
            self._clients = {SourceId.TMDB: tmdb, **supplements}

    def _load_supplements(self) -> dict[SourceId, BaseMetadataClient]:
        trakt = None
        omdb = None
        try:
            stored = SourceCredentialStore(SourceId.TRAKT).load()
            trakt = stored.value if stored else None
        except (OSError, PermissionError, ValueError):
            trakt = None
        try:
            stored = SourceCredentialStore(SourceId.OMDB).load()
            omdb = stored.value if stored else None
        except (OSError, PermissionError, ValueError):
            omdb = None
        return build_supplement_clients(
            trakt_client_id=trakt,
            omdb_api_key=omdb,
            omdb_acknowledged=self.settings.omdb_non_commercial_acknowledged(),
        )

    def client(self, source_id: SourceId | str) -> MetadataClient:
        return self._clients[SourceId(source_id)]

    def refresh_supplements(self) -> None:
        """Reload Trakt/OMDb credentials and OMDb ToS gate after Settings changes."""
        supplements = self._load_supplements()
        self._clients.update(supplements)

    def set_tmdb_client(self, client: TmdbClient) -> None:
        self._clients[SourceId.TMDB] = TmdbMetadataClient(client)

    def candidates(self, capability: Capability) -> list[MetadataClient]:
        """Enabled sources that expose the capability, in routing priority order."""
        result: list[MetadataClient] = []
        for source_id in _SOURCE_PRIORITY:
            if capability not in self.settings.enabled_capabilities(source_id):
                continue
            client = self._clients[source_id]
            if capability in client.supported_capabilities():
                result.append(client)
        return result

    def resolve(self, capability: Capability) -> MetadataClient:
        """Pick an implemented client, preferring TMDb, then other enabled sources."""
        for client in self.candidates(capability):
            if client.supports(capability):
                return client
        # Soft fallback: TMDb always remains available for core catalog capabilities.
        tmdb = self._clients[SourceId.TMDB]
        if capability in tmdb.supported_capabilities() and tmdb.supports(capability):
            return tmdb
        label = capability.value
        raise UnsupportedCapabilityError(
            f"Etkin bir metadata kaynağı {label} yeteneğini karşılamıyor."
        )

    def matrix(self) -> list[dict[str, object]]:
        """Capability × source overview for docs/tests/Settings."""
        rows: list[dict[str, object]] = []
        for capability in Capability:
            row: dict[str, object] = {"capability": capability.value, "sources": {}}
            sources: dict[str, dict[str, bool]] = {}
            for source_id, definition in SOURCE_CATALOG.items():
                supported = capability in definition.supported
                enabled = capability in self.settings.enabled_capabilities(source_id)
                implemented = (
                    capability
                    in self._clients[source_id].implemented_capabilities()
                )
                sources[source_id.value] = {
                    "supported": supported,
                    "enabled": enabled,
                    "implemented": implemented,
                }
            row["sources"] = sources
            rows.append(row)
        return rows
