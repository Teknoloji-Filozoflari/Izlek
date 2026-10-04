"""AppImage metadata, resource, and user-directory regression tests."""

import configparser
import os
import runpy
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType, SimpleNamespace

from scripts import build_deb

from izlek.cache.images import ImageDiskCache
from izlek.core.paths import app_paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pyinstaller_spec_resolves_entrypoint_and_resources(monkeypatch):
    """SPECPATH is a directory, including when run outside the repository."""
    hooks = ModuleType("PyInstaller.utils.hooks")
    hooks.collect_submodules = lambda name: []
    hooks.copy_metadata = lambda name: []
    monkeypatch.setitem(sys.modules, "PyInstaller.utils.hooks", hooks)
    captured = {}

    def analysis(scripts, **kwargs):
        captured.update(scripts=scripts, **kwargs)
        return SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[])

    spec = PROJECT_ROOT / "packaging/izlek.spec"
    runpy.run_path(str(spec), init_globals={
        "SPECPATH": str(spec.parent), "Analysis": analysis,
        "PYZ": lambda *args, **kwargs: None,
        "EXE": lambda *args, **kwargs: None,
        "COLLECT": lambda *args, **kwargs: None,
    })
    assert captured["scripts"] == [str(PROJECT_ROOT / "src/izlek/__main__.py")]
    assert all(Path(source).exists() for source, _ in captured["datas"])
    assert any(
        destination == "izlek/db/migrations/versions"
        for _, destination in captured["datas"]
    )


def test_release_version_and_artifact_names_are_consistent():
    project = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    version = project["project"]["version"]
    assert (PROJECT_ROOT / f"docs/release-notes/v{version}.md").is_file()
    assert f"version: '{version}'" in (
        PROJECT_ROOT / "snap/snapcraft.yaml"
    ).read_text(encoding="utf-8")

    release = (PROJECT_ROOT / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )
    assert "Izlek-${version}-x86_64.AppImage" in release
    assert "izlek_${version}_amd64.deb" in release
    assert "Izlek-${version}-source.tar.gz" in release
    assert 'docs/release-notes/${GITHUB_REF_NAME}.md' in release


def test_appimage_environment_does_not_change_xdg_storage(tmp_path, monkeypatch):
    home = tmp_path / "home"
    environment = {
        "APPDIR": str(tmp_path / "mount/Izlek.AppDir"),
        "APPIMAGE": str(tmp_path / "downloads/Izlek.AppImage"),
    }
    paths = app_paths(environment, home)

    assert paths.config == home / ".config/izlek"
    assert paths.data == home / ".local/share/izlek"
    assert paths.cache == home / ".cache/izlek"
    assert paths.logs == home / ".local/state/izlek/logs"

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg-cache"))
    monkeypatch.setenv("APPDIR", environment["APPDIR"])
    assert ImageDiskCache().root == tmp_path / "xdg-cache/izlek/images"


def test_package_smoke_mode_writes_only_to_isolated_user_dirs(tmp_path):
    fake_appdir = tmp_path / "mounted-appimage"
    fake_appdir.mkdir()
    fake_appimage = tmp_path / "Izlek.AppImage"
    fake_appimage.write_bytes(b"immutable")
    user_root = tmp_path / "user"
    environment = os.environ | {
        "APPDIR": str(fake_appdir),
        "APPIMAGE": str(fake_appimage),
        "HOME": str(user_root / "home"),
        "XDG_CONFIG_HOME": str(user_root / "config"),
        "XDG_DATA_HOME": str(user_root / "data"),
        "XDG_CACHE_HOME": str(user_root / "cache"),
        "XDG_STATE_HOME": str(user_root / "state"),
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
    }

    result = subprocess.run(
        [sys.executable, "-m", "izlek", "--package-smoke-test"],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert (user_root / "data/izlek/izlek.sqlite3").is_file()
    assert (user_root / "config/izlek/window.ini").is_file()
    assert not any(fake_appdir.iterdir())
    assert fake_appimage.read_bytes() == b"immutable"


def test_appdir_metadata_and_pyinstaller_resources_are_complete():
    desktop = configparser.ConfigParser(interpolation=None)
    desktop.read(
        PROJECT_ROOT / "src/izlek/resources/desktop/izlek.desktop",
        encoding="utf-8",
    )
    entry = desktop["Desktop Entry"]
    assert entry["Name"] == "İzlek"
    assert entry["Exec"] == "izlek"
    assert entry["Icon"] == "izlek"
    assert entry.getboolean("Terminal") is False
    assert {"AudioVideo", "Video"} <= set(entry["Categories"].split(";"))

    app_run = (PROJECT_ROOT / "packaging/AppRun").read_text(encoding="utf-8")
    assert 'exec "$APPDIR/usr/lib/izlek/izlek" "$@"' in app_run
    assert "XDG_" not in app_run

    spec = (PROJECT_ROOT / "packaging/izlek.spec").read_text(encoding="utf-8")
    for bundled_path in ("ui/qml", "resources", "db/migrations"):
        assert bundled_path in spec
    assert "COLLECT(" in spec

    constraints = (
        PROJECT_ROOT / "packaging/constraints-appimage.txt"
    ).read_text(encoding="utf-8")
    assert "PySide6==6.8.2.1" in constraints


def test_appimage_build_command_is_discoverable():
    result = subprocess.run(
        [sys.executable, "scripts/build_appimage.py", "--help"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--appdir-only" in result.stdout
    assert "--appimagetool" in result.stdout
    assert "--runtime-file" in result.stdout


def test_debian_package_metadata_and_build_command_are_discoverable():
    control = (
        PROJECT_ROOT / "packaging/debian/control.in"
    ).read_text(encoding="utf-8")
    assert "Package: izlek" in control
    assert "Version: @VERSION@" in control
    assert "Architecture: @ARCHITECTURE@" in control
    assert "Maintainer: @MAINTAINER@" in control
    assert "Homepage: @HOMEPAGE@" in control
    assert "libxkbcommon-x11-0" in control

    result = subprocess.run(
        [sys.executable, "scripts/build_deb.py", "--help"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--skip-onedir-build" in result.stdout
    assert "--homepage" in result.stdout
    assert "--maintainer" in result.stdout


def test_debian_stage_renders_release_metadata(tmp_path, monkeypatch):
    onedir = tmp_path / "onedir"
    onedir.mkdir()
    (onedir / "izlek").write_text("binary", encoding="utf-8")
    monkeypatch.setattr(build_deb, "ONEDIR", onedir)

    staged = build_deb.stage_package(
        tmp_path / "stage",
        "1.0.0",
        "amd64",
        homepage="https://github.com/example/Izlek",
        maintainer="İzlek contributors <example@users.noreply.github.com>",
    )
    control = (staged / "DEBIAN/control").read_text(encoding="utf-8")
    copyright_text = (staged / "usr/share/doc/izlek/copyright").read_text(
        encoding="utf-8"
    )

    assert "Version: 1.0.0" in control
    assert "Architecture: amd64" in control
    assert "Homepage: https://github.com/example/Izlek" in control
    assert "example@users.noreply.github.com" in control
    assert "@" not in copyright_text
    assert "https://github.com/example/Izlek" in copyright_text
