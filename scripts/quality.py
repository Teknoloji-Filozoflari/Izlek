"""Run the complete local/CI quality gate with one command."""

import os
import subprocess
import sys


def main() -> int:
    """Run static checks first, then the complete offline test suite."""
    environment = os.environ.copy()
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    environment.setdefault("QT_QUICK_BACKEND", "software")
    commands = (
        ("Ruff", [sys.executable, "-m", "ruff", "check", "."]),
        ("Pytest", [sys.executable, "-m", "pytest"]),
    )
    for label, command in commands:
        print(f"==> {label}", flush=True)
        result = subprocess.run(command, env=environment, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
