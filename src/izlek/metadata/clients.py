"""Concrete metadata clients: TMDb adapter plus capability-gated supplements."""

from __future__ import annotations

from izlek.metadata.capabilities import Capability
from izlek.metadata.catalog import SOURCE_CATALOG, SourceId
from izlek.metadata.protocol import UnsupportedCapabilityError
from izlek.tmdb.client import TmdbClient


class BaseMetadataClient:
    """Shared capability helpers for catalog-backed clients."""

    source_id: SourceId

    def supported_capabilities(self) -> frozenset[Capability]:
        return SOURCE_CATALOG[self.source_id].supported

    def implemented_capabilities(self) -> frozenset[Capability]:
        return frozenset()

    def supports(self, capability: Capability) -> bool:
        return capability in self.implemented_capabilities()

    def require(self, capability: Capability) -> None:
        if not self.supports(capability):
            label = SOURCE_CATALOG[self.source_id].label
            raise UnsupportedCapabilityError(
                f"{label} şu anda {capability.value} yeteneğini uygulamıyor."
            )


class TmdbMetadataClient(BaseMetadataClient):
    """Adapt the existing TMDb HTTP client to the shared metadata interface."""

    source_id = SourceId.TMDB

    def __init__(self, client: TmdbClient | None = None) -> None:
        self.client = client or TmdbClient()

    def implemented_capabilities(self) -> frozenset[Capability]:
        return self.supported_capabilities()

    def __getattr__(self, name: str):
        return getattr(self.client, name)


class TraktMetadataClient(BaseMetadataClient):
    """Trakt wiring: credentials + capability matrix; HTTP fetch lands later."""

    source_id = SourceId.TRAKT

    def __init__(self, client_id: str | None = None) -> None:
        self.client_id = (client_id or "").strip() or None


class TvmazeMetadataClient(BaseMetadataClient):
    """TVmaze wiring for TV-only capabilities; HTTP fetch lands later."""

    source_id = SourceId.TVMAZE


class OmdbMetadataClient(BaseMetadataClient):
    """OMDb title-lookup client gated to non-commercial acknowledgment."""

    source_id = SourceId.OMDB

    def __init__(
        self,
        api_key: str | None = None,
        *,
        non_commercial_acknowledged: bool = False,
    ) -> None:
        self.api_key = (api_key or "").strip() or None
        self.non_commercial_acknowledged = non_commercial_acknowledged

    def implemented_capabilities(self) -> frozenset[Capability]:
        if self.non_commercial_acknowledged and self.api_key:
            return frozenset({Capability.TITLE_LOOKUP})
        return frozenset()

    def title_lookup(self, *, imdb_id: str = "", title: str = "") -> dict[str, str]:
        """Placeholder until the OMDb HTTP path is added in a later PR."""
        self.require(Capability.TITLE_LOOKUP)
        if not imdb_id and not title:
            raise UnsupportedCapabilityError("OMDb için imdb_id veya title gerekli.")
        raise UnsupportedCapabilityError(
            "OMDb HTTP istemcisi henüz etkin değil; yalnızca ayar ve ToS kapısı hazır."
        )


def build_supplement_clients(
    *,
    trakt_client_id: str | None = None,
    omdb_api_key: str | None = None,
    omdb_acknowledged: bool = False,
) -> dict[SourceId, BaseMetadataClient]:
    """Construct non-TMDb clients from stored credentials and ToS state."""
    return {
        SourceId.TRAKT: TraktMetadataClient(trakt_client_id),
        SourceId.TVMAZE: TvmazeMetadataClient(),
        SourceId.OMDB: OmdbMetadataClient(
            omdb_api_key, non_commercial_acknowledged=omdb_acknowledged
        ),
    }
