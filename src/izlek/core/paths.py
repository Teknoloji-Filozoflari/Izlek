"""Resolve user directories for Linux/XDG and Windows/AppData."""

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    """Application-owned directories; resolution does not create them."""

    config: Path
    data: Path
    cache: Path
    logs: Path


def _xdg_base(env: Mapping[str, str], name: str, fallback: Path) -> Path:
    value = env.get(name, "")
    candidate = Path(value) if value else fallback
    return candidate if candidate.is_absolute() else fallback


def app_paths(
    env: Mapping[str, str] | None = None, home: Path | None = None
) -> AppPaths:
    """Return native paths while honoring absolute XDG development overrides."""
    variables = os.environ if env is None else env
    user_home = Path.home() if home is None else home
    if sys.platform == "win32":
        roaming = _xdg_base(variables, "APPDATA", user_home / "AppData/Roaming")
        local = _xdg_base(variables, "LOCALAPPDATA", user_home / "AppData/Local")

        def owned(name: str, fallback: Path) -> Path:
            value = variables.get(name, "")
            if value and Path(value).is_absolute():
                return Path(value) / "izlek"
            return fallback

        return AppPaths(
            config=owned("XDG_CONFIG_HOME", roaming / "izlek"),
            data=owned("XDG_DATA_HOME", local / "izlek"),
            cache=owned("XDG_CACHE_HOME", local / "izlek/cache"),
            logs=owned("XDG_STATE_HOME", local / "izlek") / "logs",
        )
    config = _xdg_base(variables, "XDG_CONFIG_HOME", user_home / ".config")
    data = _xdg_base(variables, "XDG_DATA_HOME", user_home / ".local/share")
    cache = _xdg_base(variables, "XDG_CACHE_HOME", user_home / ".cache")
    state = _xdg_base(variables, "XDG_STATE_HOME", user_home / ".local/state")
    return AppPaths(
        config=config / "izlek",
        data=data / "izlek",
        cache=cache / "izlek",
        logs=state / "izlek" / "logs",
    )
