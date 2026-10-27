"""Turn TMDb watch-provider metadata into clear local UI groups."""

from collections.abc import Mapping
from typing import Any

# Stable Turkish labels used as dict keys in QML (matches existing call sites).
PROVIDER_GROUPS = (
    ("Abonelik", "flatrate"),
    ("Ücretsiz", "free"),
    ("Reklamlı", "ads"),
    ("Kiralama", "rent"),
    ("Satın Alma", "buy"),
)

PROVIDER_GROUP_HINTS = {
    "Abonelik": "Abonelik / SVOD",
    "Ücretsiz": "Ücretsiz izleme",
    "Reklamlı": "Reklamlı / AVOD",
    "Kiralama": "Kiralama",
    "Satın Alma": "Satın alma",
}


def present_providers(
    region: Mapping[str, Any] | None,
) -> tuple[dict[str, list[str]], str]:
    """Keep subscription, free, ads, rental, and purchase rows for the region.

    Empty groups are still returned so the UI can hide them consistently.
    Free/ads rows are informational only (no deeplinks).
    """
    region = region or {}
    groups = {
        label: [
            str(provider.get("provider_name", ""))
            for provider in region.get(key, [])
            if isinstance(provider, Mapping) and provider.get("provider_name")
        ]
        for label, key in PROVIDER_GROUPS
    }
    link = region.get("link", "")
    if not isinstance(link, str) or not link.startswith("https://www.themoviedb.org/"):
        link = ""
    return groups, link
