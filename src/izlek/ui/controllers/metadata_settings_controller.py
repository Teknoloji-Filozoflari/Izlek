"""QML bridge for metadata sources, capability toggles, and watch region."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from izlek.metadata.capabilities import Capability
from izlek.metadata.catalog import (
    WATCH_PROVIDER_REGIONS,
    SourceId,
    normalize_watch_region,
)
from izlek.metadata.credentials import SourceCredentialStore
from izlek.metadata.registry import MetadataClientRegistry
from izlek.metadata.settings import MetadataSettings


class MetadataSettingsController(QObject):
    """Expose configurable metadata sources without blocking the UI thread."""

    changed = Signal()
    regionChanged = Signal(str)

    def __init__(
        self,
        settings: MetadataSettings | None = None,
        registry: MetadataClientRegistry | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings or MetadataSettings()
        self._registry = registry
        self._feedback = ""
        self._feedback_kind = "neutral"
        self._editing_source = ""
        self._credential_draft = ""

    def _notify(self) -> None:
        self.changed.emit()

    @Property("QVariantList", notify=changed)
    def sources(self) -> list[dict[str, Any]]:
        snapshot = self._settings.snapshot()["sources"]
        order = [SourceId.TMDB, SourceId.TRAKT, SourceId.TVMAZE, SourceId.OMDB]
        result: list[dict[str, Any]] = []
        for source_id in order:
            entry = dict(snapshot[source_id.value])
            entry["hasCredential"] = self._has_credential(source_id)
            entry["isDefault"] = source_id is SourceId.TMDB
            entry["requiresNonCommercialAck"] = source_id is SourceId.OMDB
            result.append(entry)
        return result

    @Property(str, notify=changed)
    def watchProviderRegion(self) -> str:
        return self._settings.watch_provider_region

    @Property("QVariantList", notify=changed)
    def watchProviderRegions(self) -> list[dict[str, str]]:
        return [
            {"code": code, "label": label} for code, label in WATCH_PROVIDER_REGIONS
        ]

    @Property(str, notify=changed)
    def feedback(self) -> str:
        return self._feedback

    @Property(str, notify=changed)
    def feedbackKind(self) -> str:
        return self._feedback_kind

    @Slot(str)
    def setWatchProviderRegion(self, code: str) -> None:
        region = self._settings.set_watch_provider_region(code)
        self._feedback = f"İzleme bölgesi {region} olarak ayarlandı."
        self._feedback_kind = "success"
        self.regionChanged.emit(region)
        self._notify()

    @Slot(str, bool)
    def setSourceEnabled(self, source_id: str, enabled: bool) -> None:
        try:
            self._settings.set_source_enabled(source_id, enabled)
        except ValueError as exc:
            self._feedback = str(exc)
            self._feedback_kind = "danger"
            self._notify()
            return
        label = SourceId(source_id).value
        if SourceId(source_id) is SourceId.TMDB and not enabled:
            self._feedback = "TMDb varsayılan kaynak olarak açık kalır."
            self._feedback_kind = "warning"
        else:
            state = "açıldı" if self._settings.is_enabled(source_id) else "kapatıldı"
            self._feedback = f"{label} kaynağı {state}."
            self._feedback_kind = "success"
        self._refresh_registry()
        self._notify()

    @Slot(str, str, bool)
    def setSourceCapability(
        self, source_id: str, capability: str, enabled: bool
    ) -> None:
        try:
            self._settings.set_capability(
                source_id, Capability(capability), enabled
            )
        except ValueError as exc:
            self._feedback = str(exc)
            self._feedback_kind = "danger"
            self._notify()
            return
        self._feedback = "Kaynak yetenekleri güncellendi."
        self._feedback_kind = "success"
        self._refresh_registry()
        self._notify()

    @Slot(bool)
    def acknowledgeOmdbNonCommercial(self, acknowledged: bool) -> None:
        self._settings.acknowledge_omdb_non_commercial(acknowledged)
        if acknowledged:
            self._feedback = (
                "OMDb ticari olmama onayı kaydedildi. "
                "Anahtar ekleyip kaynağı açabilirsiniz."
            )
            self._feedback_kind = "success"
        else:
            self._feedback = "OMDb onayı kaldırıldı; kaynak kapatıldı."
            self._feedback_kind = "warning"
        self._refresh_registry()
        self._notify()

    @Slot(str, str)
    def saveSourceCredential(self, source_id: str, value: str) -> None:
        key = SourceId(source_id)
        if key is SourceId.TMDB:
            self._feedback = "TMDb tokenı üstteki TMDb kartından yönetilir."
            self._feedback_kind = "warning"
            self._notify()
            return
        if key is SourceId.TVMAZE:
            self._feedback = "TVmaze genel API anahtarı gerektirmez."
            self._feedback_kind = "neutral"
            self._notify()
            return
        try:
            location = SourceCredentialStore(key).save(value.strip())
        except ValueError as exc:
            self._feedback = str(exc)
            self._feedback_kind = "danger"
            self._notify()
            return
        backend = "sistem anahtarlığı" if location == "keyring" else "yerel dosya"
        self._feedback = f"{key.value} kimliği {backend} ile kaydedildi."
        self._feedback_kind = "success"
        self._refresh_registry()
        self._notify()

    @Slot(str)
    def clearSourceCredential(self, source_id: str) -> None:
        key = SourceId(source_id)
        if key in (SourceId.TMDB, SourceId.TVMAZE):
            return
        SourceCredentialStore(key).clear()
        self._feedback = f"{key.value} kimliği silindi."
        self._feedback_kind = "success"
        self._refresh_registry()
        self._notify()

    def _has_credential(self, source_id: SourceId) -> bool:
        if source_id is SourceId.TMDB:
            return True
        if source_id is SourceId.TVMAZE:
            return True
        try:
            return SourceCredentialStore(source_id).load() is not None
        except (OSError, PermissionError):
            return False

    def _refresh_registry(self) -> None:
        if self._registry is not None:
            self._registry.refresh_supplements()

    def region_code(self) -> str:
        return normalize_watch_region(self._settings.watch_provider_region)
