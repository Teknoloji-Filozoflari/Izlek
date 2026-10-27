"""Configurable metadata sources and capability routing."""

from izlek.metadata.capabilities import Capability
from izlek.metadata.catalog import SOURCE_CATALOG, SourceId
from izlek.metadata.protocol import (
    MetadataClient,
    MetadataError,
    UnsupportedCapabilityError,
)
from izlek.metadata.registry import MetadataClientRegistry
from izlek.metadata.settings import MetadataSettings

__all__ = [
    "Capability",
    "SOURCE_CATALOG",
    "SourceId",
    "MetadataClient",
    "MetadataError",
    "UnsupportedCapabilityError",
    "MetadataClientRegistry",
    "MetadataSettings",
]
