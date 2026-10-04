"""Validate bundle boundaries and revision-independent Snap storage."""

import os
import subprocess
import sys
import tarfile
from pathlib import Path

from scripts import build_rpm

ROOT = Path(__file__).resolve().parents[1]


def test_rpm_source_contains_payload_and_public_assets_only(tmp_path, monkeypatch):
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "izlek").write_text("application")
    (payload / "_internal").mkdir()
    (payload / "_internal/resource.qml").write_text("qml")
    monkeypatch.setattr(build_rpm, "ONEDIR", payload)
    archive = build_rpm.stage_source(tmp_path, "1.0.0")
    with tarfile.open(archive) as source:
        names = source.getnames()
    assert "izlek-1.0.0/payload/izlek" in names
    assert "izlek-1.0.0/payload/_internal/resource.qml" in names
    assert "izlek-1.0.0/izlek.desktop" in names
    assert "izlek-1.0.0/LICENSE" in names
    assert not any(".venv" in name or "sqlite" in name for name in names)


def test_rpm_help_does_not_require_build_tools():
    result = subprocess.run(
        [sys.executable, "scripts/build_rpm.py", "--help"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    assert "--skip-onedir-build" in result.stdout
    assert "--output-dir" in result.stdout


def test_snap_launcher_preserves_arguments_and_uses_common_storage(tmp_path):
    snap = tmp_path / "snap with spaces"
    binary = snap / "usr/lib/izlek/izlek"
    binary.parent.mkdir(parents=True)
    binary.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" '
        '"$XDG_CACHE_HOME" "$XDG_STATE_HOME" "$@"\n'
    )
    binary.chmod(0o755)
    common = tmp_path / "common"
    result = subprocess.run(
        ["sh", str(ROOT / "snap/local/izlek-launcher"), "file with spaces.json"],
        env=os.environ | {"SNAP": str(snap), "SNAP_USER_COMMON": str(common)},
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.splitlines() == [
        str(common / folder) for folder in ("config", "data", "cache", "state")
    ] + ["file with spaces.json"]
