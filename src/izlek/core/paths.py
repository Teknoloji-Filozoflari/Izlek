"""Resolve İzlek directories using the XDG Base Directory specification."""

import os
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
    """Return XDG paths, ignoring relative or empty XDG overrides."""
    variables = os.environ if env is None else env
    user_home = Path.home() if home is None else home
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
