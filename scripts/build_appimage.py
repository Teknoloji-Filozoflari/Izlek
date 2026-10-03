"""Build, smoke-test, and package the PyInstaller bundle as an AppImage."""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_FILE = PROJECT_ROOT / "packaging/izlek.spec"
ONEDIR = PROJECT_ROOT / "dist/izlek"
APPDIR = PROJECT_ROOT / "build/appimage/Izlek.AppDir"


def _run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, env=env, check=True)


def _version() -> str:
    try:
        return version("izlek")
    except PackageNotFoundError:
        return "1.0.0"


def _tree_files(root: Path) -> set[Path]:
    return {path.relative_to(root) for path in root.rglob("*") if path.is_file()}


def _smoke_environment(root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("APPDIR", None)
    environment.pop("APPIMAGE", None)
    environment.update(
        {
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QUICK_BACKEND": "software",
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_STATE_HOME": str(root / "state"),
        }
    )
    return environment


def smoke(executable: Path, *, immutable_root: Path | None = None) -> None:
    """Open packaged QML offscreen and assert all writes stay in XDG paths."""
    before = _tree_files(immutable_root) if immutable_root is not None else set()
    with TemporaryDirectory(prefix="izlek-package-smoke-") as temporary:
        root = Path(temporary)
        environment = _smoke_environment(root)
        _run([str(executable), "--package-smoke-test"], env=environment)
        assert (root / "data/izlek/izlek.sqlite3").is_file()
        assert (root / "config/izlek/window.ini").is_file()
        if immutable_root is not None:
            assert _tree_files(immutable_root) == before


def build_onedir() -> None:
    """Build and verify the required PyInstaller one-folder bundle first."""
    _run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            str(SPEC_FILE),
        ]
    )
    executable = ONEDIR / "izlek"
    required = (
        executable,
        ONEDIR / "_internal/izlek/ui/qml/Main.qml",
        ONEDIR / "_internal/izlek/resources/icons/izlek.svg",
        ONEDIR / "_internal/izlek/db/migrations/env.py",
        ONEDIR / "_internal/izlek/db/migrations/versions/0003_season_freshness.py",
    )
    missing = [
        str(path.relative_to(PROJECT_ROOT))
        for path in required
        if not path.exists()
    ]
    if missing:
        raise RuntimeError("One-folder kaynakları eksik: " + ", ".join(missing))
    smoke(executable, immutable_root=ONEDIR)


def create_appdir() -> Path:
    """Create a standards-shaped AppDir around the verified one-folder build."""
    if APPDIR.exists():
        shutil.rmtree(APPDIR)
    application_dir = APPDIR / "usr/lib/izlek"
    application_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ONEDIR, application_dir)

    binary_link = APPDIR / "usr/bin/izlek"
    binary_link.parent.mkdir(parents=True, exist_ok=True)
    binary_link.symlink_to("../lib/izlek/izlek")

    app_run = APPDIR / "AppRun"
    shutil.copy2(PROJECT_ROOT / "packaging/AppRun", app_run)
    app_run.chmod(0o755)

    desktop_source = PROJECT_ROOT / "src/izlek/resources/desktop/izlek.desktop"
    desktop_text = desktop_source.read_text(encoding="utf-8")
    desktop_text += (
        f"X-AppImage-Name=İzlek\n"
        f"X-AppImage-Version={_version()}\n"
        f"X-AppImage-Arch={platform.machine()}\n"
    )
    desktop_target = APPDIR / "usr/share/applications/izlek.desktop"
    desktop_target.parent.mkdir(parents=True, exist_ok=True)
    desktop_target.write_text(desktop_text, encoding="utf-8")
    (APPDIR / "izlek.desktop").symlink_to("usr/share/applications/izlek.desktop")

    icon_source = PROJECT_ROOT / "src/izlek/resources/icons/izlek.svg"
    icon_target = APPDIR / "usr/share/icons/hicolor/scalable/apps/izlek.svg"
    icon_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(icon_source, icon_target)
    (APPDIR / "izlek.svg").symlink_to(
        "usr/share/icons/hicolor/scalable/apps/izlek.svg"
    )
    (APPDIR / ".DirIcon").symlink_to("izlek.svg")

    license_target = APPDIR / "usr/share/doc/izlek/LICENSE"
    license_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "LICENSE", license_target)
    return APPDIR


def build_appimage(appimagetool: Path, runtime_file: Path | None = None) -> Path:
    """Turn the prepared AppDir into the final x86_64 AppImage."""
    architecture = platform.machine()
    if architecture != "x86_64":
        raise RuntimeError(
            "Bu fazın glibc 2.28 constraint'i yalnız x86_64 için doğrulandı: "
            f"{architecture}"
        )
    output = PROJECT_ROOT / f"dist/Izlek-{_version()}-{architecture}.AppImage"
    environment = os.environ.copy()
    environment.update(
        {
            "ARCH": architecture,
            "VERSION": _version(),
            "APPIMAGE_EXTRACT_AND_RUN": "1",
        }
    )
    command = [str(appimagetool)]
    if runtime_file is not None:
        command.extend(["--runtime-file", str(runtime_file.resolve())])
    command.extend([str(APPDIR), str(output)])
    _run(command, env=environment)
    output.chmod(output.stat().st_mode | 0o111)
    smoke(output, immutable_root=output.parent)
    with output.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.name}\n", encoding="ascii"
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--appdir-only",
        action="store_true",
        help="One-folder ve AppDir doğrulamasından sonra dur.",
    )
    parser.add_argument(
        "--appimagetool",
        type=Path,
        help="AppImage üretmek için appimagetool yolu.",
    )
    parser.add_argument(
        "--runtime-file",
        type=Path,
        help="Ağsız üretim için önceden indirilmiş type2 runtime yolu.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if find_spec("PyInstaller") is None:
        print(
            "PyInstaller bulunamadı. Önce -e '.[package]' bağımlılıklarını kurun.",
            file=sys.stderr,
        )
        return 2
    build_onedir()
    create_appdir()
    smoke(APPDIR / "AppRun", immutable_root=APPDIR)
    if args.appdir_only:
        print(f"AppDir hazır: {APPDIR}")
        return 0
    tool = args.appimagetool or (
        Path(candidate) if (candidate := shutil.which("appimagetool")) else None
    )
    if tool is None or not tool.is_file():
        print("appimagetool bulunamadı; --appimagetool ile yol verin.", file=sys.stderr)
        return 2
    if args.runtime_file is not None and not args.runtime_file.is_file():
        print(f"Runtime bulunamadı: {args.runtime_file}", file=sys.stderr)
        return 2
    output = build_appimage(tool.resolve(), args.runtime_file)
    print(f"AppImage hazır: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
