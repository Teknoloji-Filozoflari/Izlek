"""Load flat/nested JSON locale packs and resolve dotted keys."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_LOCALE = "tr"
AVAILABLE_LOCALES = ("tr", "en", "az", "es", "ru", "tk", "uz", "kk")
_LOCALE_DIR = Path(__file__).resolve().parent / "locales"
_FALLBACK_TMDB = {
    "tr": "tr-TR",
    "en": "en-US",
    "az": "az-AZ",
    "es": "es-ES",
    "ru": "ru-RU",
    "tk": "en-US",
    "uz": "uz-UZ",
    "kk": "kk-KZ",
}

_packs: dict[str, dict[str, Any]] = {}
_current = DEFAULT_LOCALE


def _deep_get(data: dict[str, Any], key: str) -> Any:
    node: Any = data
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        elif isinstance(value, str):
            flat[path] = value
    return flat


def load_locale_pack(code: str) -> dict[str, Any]:
    """Return one locale pack; cache after first disk read."""
    normalized = (code or DEFAULT_LOCALE).lower().replace("_", "-")
    short = normalized.split("-", 1)[0]
    if short not in AVAILABLE_LOCALES:
        short = DEFAULT_LOCALE
    cached = _packs.get(short)
    if cached is not None:
        return cached
    path = _LOCALE_DIR / f"{short}.json"
    with path.open(encoding="utf-8") as handle:
        pack = json.load(handle)
    if not isinstance(pack, dict):
        raise ValueError(f"Locale pack must be an object: {path}")
    _packs[short] = pack
    return pack


def available_locales() -> list[dict[str, str]]:
    """Stable language picker rows: code, English name, native name."""
    rows: list[dict[str, str]] = []
    for code in AVAILABLE_LOCALES:
        meta = load_locale_pack(code).get("meta", {})
        rows.append(
            {
                "code": code,
                "name": str(meta.get("name", code)),
                "nativeName": str(meta.get("nativeName", code)),
            }
        )
    return rows


def get_locale() -> str:
    return _current


def set_locale(code: str) -> str:
    """Activate a supported locale; unknown codes fall back to Turkish."""
    global _current
    normalized = (code or DEFAULT_LOCALE).lower().replace("_", "-")
    short = normalized.split("-", 1)[0]
    if short not in AVAILABLE_LOCALES:
        short = DEFAULT_LOCALE
    load_locale_pack(short)
    _current = short
    return _current


def tmdb_language(code: str | None = None) -> str:
    """TMDb `language` query value for the active (or given) UI locale."""
    locale = (code or _current).lower().split("-", 1)[0]
    pack = load_locale_pack(locale if locale in AVAILABLE_LOCALES else DEFAULT_LOCALE)
    meta = pack.get("meta", {})
    configured = meta.get("tmdb")
    if isinstance(configured, str) and configured:
        return configured
    return _FALLBACK_TMDB.get(locale, "en-US")


def t(key: str, **kwargs: object) -> str:
    """Translate a dotted key; fall back to Turkish, then the key itself."""
    if not key:
        return ""
    for locale in (_current, DEFAULT_LOCALE):
        pack = load_locale_pack(locale)
        value = _deep_get(pack, key)
        if isinstance(value, str):
            if kwargs:
                try:
                    return value.format(**kwargs)
                except (KeyError, ValueError, IndexError):
                    return value
            return value
    return key


def catalog_keys(code: str = DEFAULT_LOCALE) -> set[str]:
    """Flattened key set for parity tests."""
    pack = deepcopy(load_locale_pack(code))
    pack.pop("meta", None)
    return set(_flatten(pack))
