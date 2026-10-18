"""Run this source checkout with workspace-local data and no system keyring."""

import os
import sys
from pathlib import Path


def main() -> int:
    """Keep development databases, settings and credentials apart from installs."""
    root = Path(__file__).resolve().parents[1]
    user_root = root / ".dev-data"
    for name, directory in (
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_DATA_HOME", "data"),
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_STATE_HOME", "state"),
    ):
        os.environ[name] = str(user_root / directory)
    os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"
    sys.path.insert(0, str(root / "src"))

    from izlek.app import main as run_application

    return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
