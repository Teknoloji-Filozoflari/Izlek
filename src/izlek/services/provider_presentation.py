"""Turn TMDb watch-provider metadata into the three local UI groups."""

from collections.abc import Mapping
from typing import Any

PROVIDER_GROUPS = (
    ("Abonelik", "flatrate"),
    ("Kiralama", "rent"),
    ("Satın Alma", "buy"),
)


def present_providers(
    region: Mapping[str, Any] | None,
) -> tuple[dict[str, list[str]], str]:
    """Keep only TR subscription, rental, and purchase data and validate its link."""
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
