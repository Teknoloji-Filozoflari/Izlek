"""Persist metadata source toggles and watch-provider region (not secrets)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from izlek.core.paths import app_paths
from izlek.metadata.capabilities import (
    CAPABILITY_DESCRIPTIONS,
    CAPABILITY_LABELS,
    Capability,
)
from izlek.metadata.catalog import (
    DEFAULT_WATCH_PROVIDER_REGION,
    SOURCE_CATALOG,
    SourceId,
    normalize_watch_region,
)


@dataclass
class SourceSettings:
    enabled: bool
    capabilities: set[Capability] = field(default_factory=set)
    omdb_non_commercial_acknowledged: bool = False


class MetadataSettings:
    """XDG JSON settings for sources, capability matrix, and provider region."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_paths().config / "metadata-sources.json"
        self._lock = Lock()
        self._watch_provider_region = DEFAULT_WATCH_PROVIDER_REGION
        self._sources: dict[SourceId, SourceSettings] = {
            source_id: SourceSettings(
                enabled=definition.default_enabled,
                capabilities=set(definition.default_capabilities),
                omdb_non_commercial_acknowledged=False,
            )
            for source_id, definition in SOURCE_CATALOG.items()
        }
        self.load()

    @property
    def watch_provider_region(self) -> str:
        with self._lock:
            return self._watch_provider_region

    def set_watch_provider_region(self, code: str) -> str:
        region = normalize_watch_region(code)
        with self._lock:
            self._watch_provider_region = region
            self._write_unlocked()
        return region

    def source(self, source_id: SourceId | str) -> SourceSettings:
        key = SourceId(source_id)
        with self._lock:
            return SourceSettings(
                enabled=self._sources[key].enabled,
                capabilities=set(self._sources[key].capabilities),
                omdb_non_commercial_acknowledged=(
                    self._sources[key].omdb_non_commercial_acknowledged
                ),
            )

    def is_enabled(self, source_id: SourceId | str) -> bool:
        return self.source(source_id).enabled

    def enabled_capabilities(self, source_id: SourceId | str) -> frozenset[Capability]:
        settings = self.source(source_id)
        if not settings.enabled:
            return frozenset()
        definition = SOURCE_CATALOG[SourceId(source_id)]
        return frozenset(settings.capabilities & definition.supported)

    def set_source_enabled(self, source_id: SourceId | str, enabled: bool) -> None:
        key = SourceId(source_id)
        definition = SOURCE_CATALOG[key]
        with self._lock:
            current = self._sources[key]
            if (
                enabled
                and key is SourceId.OMDB
                and not current.omdb_non_commercial_acknowledged
            ):
                raise ValueError(
                    "OMDb yalnızca kişisel/ticari olmayan kullanım için "
                    "açılabilir; önce onayı işaretleyin."
                )
            if enabled and key is SourceId.TMDB and not current.capabilities:
                current.capabilities = set(definition.default_capabilities)
            current.enabled = enabled
            if key is SourceId.TMDB and not enabled:
                # Keep TMDb as the always-available fallback for core catalog.
                current.enabled = True
            self._write_unlocked()

    def set_capability(
        self, source_id: SourceId | str, capability: Capability | str, enabled: bool
    ) -> None:
        key = SourceId(source_id)
        cap = Capability(capability)
        definition = SOURCE_CATALOG[key]
        if cap not in definition.supported:
            raise ValueError(f"{definition.label} {cap} yeteneğini desteklemiyor.")
        with self._lock:
            current = self._sources[key]
            if enabled:
                current.capabilities.add(cap)
            else:
                current.capabilities.discard(cap)
            self._write_unlocked()

    def acknowledge_omdb_non_commercial(self, acknowledged: bool = True) -> None:
        with self._lock:
            current = self._sources[SourceId.OMDB]
            current.omdb_non_commercial_acknowledged = acknowledged
            if not acknowledged:
                current.enabled = False
            self._write_unlocked()

    def omdb_non_commercial_acknowledged(self) -> bool:
        return self.source(SourceId.OMDB).omdb_non_commercial_acknowledged

    def snapshot(self) -> dict[str, Any]:
        """Serializable view for QML / tests."""
        with self._lock:
            return {
                "watchProviderRegion": self._watch_provider_region,
                "sources": {
                    source_id.value: {
                        "id": source_id.value,
                        "label": definition.label,
                        "summary": definition.summary,
                        "notes": definition.notes,
                        "enabled": settings.enabled,
                        "credentialKind": definition.credential_kind.value,
                        "credentialLabel": definition.credential_label,
                        "commercialPolicy": definition.commercial_policy.value,
                        "omdbNonCommercialAcknowledged": (
                            settings.omdb_non_commercial_acknowledged
                        ),
                        "capabilities": [
                            {
                                "id": capability.value,
                                "label": CAPABILITY_LABELS[capability],
                                "description": CAPABILITY_DESCRIPTIONS[capability],
                                "supported": True,
                                "enabled": capability in settings.capabilities,
                            }
                            for capability in sorted(
                                definition.supported, key=lambda item: item.value
                            )
                        ],
                    }
                    for source_id, definition in SOURCE_CATALOG.items()
                    for settings in (self._sources[source_id],)
                },
            }

    def load(self) -> None:
        with self._lock:
            if not self.path.is_file():
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
                return
            if not isinstance(raw, dict):
                return
            region = raw.get("watchProviderRegion") or raw.get("watch_provider_region")
            self._watch_provider_region = normalize_watch_region(
                region if isinstance(region, str) else None
            )
            sources = raw.get("sources")
            if not isinstance(sources, dict):
                return
            for source_id, definition in SOURCE_CATALOG.items():
                payload = sources.get(source_id.value)
                if not isinstance(payload, dict):
                    continue
                enabled = bool(payload.get("enabled", definition.default_enabled))
                caps_raw = payload.get("capabilities", [])
                capabilities: set[Capability] = set()
                if isinstance(caps_raw, list):
                    for item in caps_raw:
                        try:
                            cap = Capability(str(item))
                        except ValueError:
                            continue
                        if cap in definition.supported:
                            capabilities.add(cap)
                acknowledged = bool(
                    payload.get("omdbNonCommercialAcknowledged")
                    or payload.get("omdb_non_commercial_acknowledged")
                )
                if source_id is SourceId.OMDB and enabled and not acknowledged:
                    enabled = False
                if source_id is SourceId.TMDB:
                    enabled = True
                    if not capabilities:
                        capabilities = set(definition.default_capabilities)
                self._sources[source_id] = SourceSettings(
                    enabled=enabled,
                    capabilities=capabilities
                    or set(definition.default_capabilities if enabled else ()),
                    omdb_non_commercial_acknowledged=acknowledged,
                )

    def _write_unlocked(self) -> None:
        payload = {
            "watchProviderRegion": self._watch_provider_region,
            "sources": {
                source_id.value: {
                    "enabled": settings.enabled,
                    "capabilities": sorted(
                        capability.value for capability in settings.capabilities
                    ),
                    "omdbNonCommercialAcknowledged": (
                        settings.omdb_non_commercial_acknowledged
                    ),
                }
                for source_id, settings in self._sources.items()
            },
        }
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        temp = self.path.with_suffix(".tmp")
        temp.write_text(encoded, encoding="utf-8")
        temp.replace(self.path)
