"""Arch PKGBUILD must pin a real published tag archive checksum."""

import re
from pathlib import Path

from scripts.verify_arch_pkgbuild import assert_srcinfo_matches, parse_pkgbuild

ROOT = Path(__file__).resolve().parents[1]
PKGBUILD = ROOT / "packaging/arch/PKGBUILD"
SRCINFO = ROOT / "packaging/arch/.SRCINFO"
README = ROOT / "packaging/arch/README.md"


def test_pkgbuild_pins_published_tag_archive_checksum():
    pkg = parse_pkgbuild(PKGBUILD)
    assert pkg["pkgver"] == "1.1.0"
    assert pkg["sha256"] != "skip"
    assert re.fullmatch(r"[0-9a-f]{64}", pkg["sha256"])
    assert pkg["source_url"].endswith(f"/archive/refs/tags/v{pkg['pkgver']}.tar.gz")
    assert_srcinfo_matches(pkg, SRCINFO)
    readme = README.read_text(encoding="utf-8")
    assert f"v{pkg['pkgver']}" in readme
    assert "SKIP" in readme  # documents that SKIP is not allowed
    assert "verify_arch_pkgbuild.py" in readme


def test_verify_arch_pkgbuild_offline_entrypoint():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "scripts/verify_arch_pkgbuild.py", "--offline"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "PKGBUILD ok" in result.stdout
