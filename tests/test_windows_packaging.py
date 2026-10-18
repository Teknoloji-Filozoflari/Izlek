"""Windows storage and installer boundaries, testable without Windows tools."""

import hashlib
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts import build_windows

import izlek.core.paths as path_module
import izlek.security.token_store as token_module


def test_windows_uses_native_profile_directories(tmp_path, monkeypatch):
    monkeypatch.setattr(path_module, "sys", SimpleNamespace(platform="win32"))
    paths = path_module.app_paths(
        {"APPDATA": str(tmp_path / "roaming"), "LOCALAPPDATA": str(tmp_path / "local")},
        tmp_path / "home",
    )
    assert paths.config == tmp_path / "roaming/izlek"
    assert paths.data == tmp_path / "local/izlek"
    assert paths.cache == tmp_path / "local/izlek/cache"
    assert paths.logs == tmp_path / "local/izlek/logs"
    assert not paths.config.exists()
    assert not paths.data.exists()


def test_windows_honors_isolated_xdg_paths_and_rejects_relative_paths(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(path_module, "sys", SimpleNamespace(platform="win32"))
    paths = path_module.app_paths(
        {
            "APPDATA": "relative",
            "LOCALAPPDATA": "relative",
            "XDG_CONFIG_HOME": str(tmp_path / "dev/config"),
            "XDG_DATA_HOME": str(tmp_path / "dev/data"),
            "XDG_CACHE_HOME": str(tmp_path / "dev/cache"),
            "XDG_STATE_HOME": str(tmp_path / "dev/state"),
        },
        tmp_path,
    )
    assert paths.config == tmp_path / "dev/config/izlek"
    assert paths.data == tmp_path / "dev/data/izlek"
    assert paths.cache == tmp_path / "dev/cache/izlek"
    assert paths.logs == tmp_path / "dev/state/izlek/logs"
    fallback = path_module.app_paths(
        {
            "APPDATA": "relative",
            "LOCALAPPDATA": "relative",
            "XDG_DATA_HOME": "relative",
        },
        tmp_path,
    )
    assert fallback.config == tmp_path / "AppData/Roaming/izlek"
    assert fallback.data == tmp_path / "AppData/Local/izlek"


def test_windows_fallback_token_does_not_apply_posix_mode_checks(tmp_path, monkeypatch):
    path = tmp_path / "tmdb-token"
    path.write_text("windows-test-only", encoding="utf-8")
    path.chmod(0o644)
    monkeypatch.setattr(token_module, "sys", SimpleNamespace(platform="win32"))
    store = token_module.TokenStore(path)
    assert store.load() == token_module.StoredToken("windows-test-only", "file")
    monkeypatch.setattr(token_module, "sys", SimpleNamespace(platform="linux"))
    with pytest.raises(PermissionError):
        store.load()


def make_bundle(directory: Path) -> Path:
    paths = [
        "izlek.exe",
        "_internal/izlek/ui/qml/Main.qml",
        "_internal/izlek/resources/icons/izlek.svg",
        "_internal/izlek/db/migrations/env.py",
        "_internal/PySide6/plugins/platforms/qwindows.dll",
    ]
    paths.extend(
        "_internal/izlek/db/migrations/versions/" + path.name
        for path in (
            build_windows.PROJECT_ROOT / "src/izlek/db/migrations/versions"
        ).glob("*.py")
    )
    for name in paths:
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"test payload")
    return directory / "izlek.exe"


def test_windows_bundle_requires_platform_plugin_and_all_migrations(tmp_path):
    executable = make_bundle(tmp_path)
    assert build_windows.validate_bundle(tmp_path) == executable
    plugin = next(tmp_path.rglob("qwindows.dll"))
    plugin.unlink()
    with pytest.raises(RuntimeError, match="qwindows.dll"):
        build_windows.validate_bundle(tmp_path)
    make_bundle(tmp_path)
    migration = (
        tmp_path / "_internal/izlek/db/migrations/versions/0005_personal_preferences.py"
    )
    migration.unlink()
    with pytest.raises(RuntimeError, match="0005_personal_preferences"):
        build_windows.validate_bundle(tmp_path)


@pytest.mark.parametrize("write_in_application", [False, True])
@pytest.mark.parametrize("native", [False, True])
def test_windows_smoke_isolates_data_and_detects_application_writes(
    tmp_path, monkeypatch, write_in_application, native
):
    executable = make_bundle(tmp_path / "application")
    user_root = tmp_path / "isolated user"

    def fake_run(command, *, env):
        assert command == [str(executable), "--package-smoke-test"]
        assert env["PYTHON_KEYRING_BACKEND"] == "keyring.backends.null.Keyring"
        assert env["QT_QPA_PLATFORM"] == "offscreen"
        if native:
            assert not any(
                name.startswith("XDG_")
                for name in env
                if name
                in {
                    "XDG_CONFIG_HOME",
                    "XDG_DATA_HOME",
                    "XDG_CACHE_HOME",
                    "XDG_STATE_HOME",
                }
            )
            targets = (("APPDATA", "window.ini"), ("LOCALAPPDATA", "izlek.sqlite3"))
        else:
            assert Path(env["XDG_CACHE_HOME"]) == user_root / "cache"
            assert Path(env["XDG_STATE_HOME"]) == user_root / "state"
            targets = (
                ("XDG_CONFIG_HOME", "window.ini"),
                ("XDG_DATA_HOME", "izlek.sqlite3"),
            )
        for variable, name in targets:
            destination = Path(env[variable]) / "izlek" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("isolated test data")
        if write_in_application:
            (executable.parent / "unexpected.sqlite3").touch()

    monkeypatch.setattr(build_windows, "run", fake_run)
    if write_in_application:
        with pytest.raises(RuntimeError, match="uygulama klasörüne"):
            build_windows.smoke(executable, user_root, native=native)
    else:
        build_windows.smoke(executable, user_root, native=native)


@pytest.mark.parametrize("delete_user_data", [False, True])
def test_installer_verification_detects_user_data_deletion(
    tmp_path, monkeypatch, delete_user_data
):
    user_databases = []

    def fake_smoke(executable, user_root, *, native):
        assert native
        path = user_root / "data/izlek/izlek.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        user_databases.append(path)

    def fake_run(command):
        if "/SP-" in command:
            destination = next(arg[5:] for arg in command if arg.startswith("/DIR="))
            make_bundle(Path(destination))
        else:
            (Path(command[0]).parent / "izlek.exe").unlink()
            if delete_user_data:
                user_databases[0].unlink()

    monkeypatch.setattr(build_windows, "run", fake_run)
    monkeypatch.setattr(build_windows, "smoke", fake_smoke)
    if delete_user_data:
        with pytest.raises(RuntimeError, match="kişisel veritabanını sildi"):
            build_windows.verify_installer(tmp_path / "setup.exe")
    else:
        build_windows.verify_installer(tmp_path / "setup.exe")


def test_build_writes_checksum_only_after_installer_verification(tmp_path, monkeypatch):
    output = tmp_path / "output with spaces"
    bundle = output / "izlek"
    installer = output / "Izlek-1.2.3-windows-x64-setup.exe"
    verified = []

    def fake_run(command):
        if "PyInstaller" in command:
            make_bundle(bundle)
            assert "--distpath" in command
        else:
            installer.write_bytes(b"MZ test installer")
            assert f"/DBundleDir={bundle}" in command

    monkeypatch.setattr(build_windows, "OUTPUT", output)
    monkeypatch.setattr(build_windows, "BUNDLE", bundle)
    monkeypatch.setattr(build_windows, "project_version", lambda: "1.2.3")
    monkeypatch.setattr(build_windows, "run", fake_run)
    monkeypatch.setattr(build_windows, "smoke", lambda *args: None)
    monkeypatch.setattr(build_windows, "verify_installer", verified.append)
    assert build_windows.build(tmp_path / "compiler.exe") == installer
    assert verified == [installer]
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    assert installer.with_suffix(".exe.sha256").read_bytes() == (
        f"{digest}  {installer.name}\n".encode()
    )


def test_windows_build_help_works_without_windows_tools():
    result = subprocess.run(
        [sys.executable, "scripts/build_windows.py", "--help"],
        cwd=build_windows.PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--iscc" in result.stdout
