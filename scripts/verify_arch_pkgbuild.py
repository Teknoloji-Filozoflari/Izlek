#!/usr/bin/env python3
"""Verify packaging/arch PKGBUILD against the published GitHub tag archive."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKGBUILD = ROOT / "packaging/arch/PKGBUILD"
SRCINFO = ROOT / "packaging/arch/.SRCINFO"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _assignment(text: str, name: str) -> str:
    match = re.search(rf"^{name}=(.+)$", text, re.MULTILINE)
    if match is None:
        raise SystemExit(f"PKGBUILD missing {name}")
    value = match.group(1).strip()
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    return value


def _expand(value: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        if name not in variables:
            raise SystemExit(f"PKGBUILD uses unknown ${{{name}}} in source")
        return variables[name]

    pattern = r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)"
    return re.sub(pattern, replace, value)


def parse_pkgbuild(path: Path = PKGBUILD) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    pkgname = _assignment(text, "pkgname")
    pkgver = _assignment(text, "pkgver")
    url = _assignment(text, "url")
    variables = {"pkgname": pkgname, "pkgver": pkgver, "url": url}
    source = _expand(_assignment(text, "source"), variables)
    digest = _assignment(text, "sha256sums").lower()
    if digest == "skip":
        raise SystemExit(
            "sha256sums must be the real published archive digest, not SKIP"
        )
    if not _HEX64.match(digest):
        raise SystemExit(f"sha256sums is not a 64-char hex digest: {digest!r}")
    if "::" in source:
        _, source_url = source.split("::", 1)
    else:
        source_url = source
    expected = f"{url}/archive/refs/tags/v{pkgver}.tar.gz"
    if source_url != expected:
        raise SystemExit(f"source URL {source_url!r} does not match {expected!r}")
    return {
        "pkgname": pkgname,
        "pkgver": pkgver,
        "url": url,
        "source_url": source_url,
        "sha256": digest,
        "text": text,
    }


def assert_srcinfo_matches(pkg: dict[str, str], path: Path = SRCINFO) -> None:
    info = path.read_text(encoding="utf-8")
    for key, needle in (
        ("pkgver", f"pkgver = {pkg['pkgver']}"),
        ("source", f"source = izlek-{pkg['pkgver']}.tar.gz::{pkg['source_url']}"),
        ("sha256sums", f"sha256sums = {pkg['sha256']}"),
    ):
        if needle not in info:
            raise SystemExit(f".SRCINFO missing expected {key} line: {needle}")


def download_sha256(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
        digest = hashlib.file_digest(response, "sha256")
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Only validate PKGBUILD/.SRCINFO shape; skip download.",
    )
    args = parser.parse_args(argv)
    pkg = parse_pkgbuild()
    assert_srcinfo_matches(pkg)
    if args.offline:
        print(
            f"PKGBUILD ok: v{pkg['pkgver']} "
            f"sha256={pkg['sha256'][:12]}… (offline)"
        )
        return 0
    actual = download_sha256(pkg["source_url"])
    if actual != pkg["sha256"]:
        raise SystemExit(
            "Published archive digest mismatch:\n"
            f"  PKGBUILD: {pkg['sha256']}\n"
            f"  download: {actual}\n"
            f"  url: {pkg['source_url']}"
        )
    print(f"Verified published source v{pkg['pkgver']}: {actual}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
