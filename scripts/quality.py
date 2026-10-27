"""Run the complete local/CI quality gate with one command."""

import os
import subprocess
import sys


def _run(label: str, command: list[str], environment: dict[str, str]) -> int:
    print(f"==> {label}", flush=True)
    return subprocess.run(command, env=environment, check=False).returncode


def main() -> int:
    """Run static checks first, then the complete offline test suite."""
    environment = os.environ.copy()
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    environment.setdefault("QT_QUICK_BACKEND", "software")
    ruff = _run("Ruff", [sys.executable, "-m", "ruff", "check", "."], environment)
    if ruff:
        return ruff
    # Offscreen Qt + Alembic can occasionally SIGSEGV under package runners;
    # retry once so release/AppImage/DEB gates are not blocked by a crash flake.
    pytest_cmd = [sys.executable, "-m", "pytest"]
    first = _run("Pytest", pytest_cmd, environment)
    if first == 0:
        return 0
    if first < 0 or first >= 128:
        print("==> Pytest crashed; retrying once", flush=True)
        return _run("Pytest (retry)", pytest_cmd, environment)
    return first


if __name__ == "__main__":
    raise SystemExit(main())
