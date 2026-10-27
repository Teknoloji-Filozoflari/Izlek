"""Shared metadata client contract used by services and the registry."""

from typing import Protocol, runtime_checkable

from izlek.metadata.capabilities import Capability
from izlek.metadata.catalog import SourceId


class MetadataError(Exception):
    """Safe domain error for metadata clients (never includes secrets)."""


class UnsupportedCapabilityError(MetadataError):
    """The selected source does not implement the requested capability yet."""


@runtime_checkable
class MetadataClient(Protocol):
    """Capability-aware metadata client. Concrete HTTP shapes stay per-source."""

    @property
    def source_id(self) -> SourceId: ...

    def supported_capabilities(self) -> frozenset[Capability]:
        """Capabilities this source can ever provide per catalog/ToS."""

    def implemented_capabilities(self) -> frozenset[Capability]:
        """Capabilities with a working client path in this build."""

    def supports(self, capability: Capability) -> bool:
        """True when the capability is both supported and implemented."""
