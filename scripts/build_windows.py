"""Build and verify the Windows x64 application and per-user EXE installer."""

import argparse
import hashlib
import os
import platform
import shutil
import struct
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "dist/windows"
BUNDLE = OUTPUT / "izlek"
SPEC = PROJECT_ROOT / "packaging/izlek.spec"
INSTALLER_SCRIPT = PROJECT_ROOT / "packaging/windows/izlek.iss"


def project_version() -> str:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as source:
        return tomllib.load(source)["project"]["version"]


def run(command: list[str], **kwargs) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True, timeout=600, **kwargs)


def validate_bundle(directory: Path) -> Path:
    """Reject incomplete payloads before compiling or distributing an installer."""
    required = [
        directory / "izlek.exe",
        directory / "_internal/izlek/ui/qml/Main.qml",
        directory / "_internal/izlek/resources/icons/izlek.svg",
        directory / "_internal/izlek/db/migrations/env.py",
    ]
    for migration in (PROJECT_ROOT / "src/izlek/db/migrations/versions").glob("*.py"):
        required.append(
            directory / "_internal/izlek/db/migrations/versions" / migration.name
        )
    missing = [
        str(path.relative_to(directory)) for path in required if not path.is_file()
    ]
    if missing:
        raise RuntimeError("Eksik Windows paket kaynakları: " + ", ".join(missing))
    if not any(directory.rglob("qwindows.dll")):
        raise RuntimeError("Windows Qt platform eklentisi qwindows.dll bulunamadı.")
    return directory / "izlek.exe"


def smoke(executable: Path, user_root: Path, *, native: bool = False) -> None:
    """Launch real bundled QML with isolated data and a disabled keyring."""
    environment = os.environ | {
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "PYTHON_KEYRING_BACKEND": "keyring.backends.null.Keyring",
        "XDG_CONFIG_HOME": str(user_root / "config"),
        "XDG_DATA_HOME": str(user_root / "data"),
        "XDG_CACHE_HOME": str(user_root / "cache"),
        "XDG_STATE_HOME": str(user_root / "state"),
    }
    if native:
        for name in (
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_CACHE_HOME",
            "XDG_STATE_HOME",
        ):
            environment.pop(name, None)
        environment["APPDATA"] = str(user_root / "config")
        environment["LOCALAPPDATA"] = str(user_root / "data")
    before = {
        path.relative_to(executable.parent) for path in executable.parent.rglob("*")
    }
    run([str(executable), "--package-smoke-test"], env=environment)
    for name in ("data/izlek/izlek.sqlite3", "config/izlek/window.ini"):
        if not (user_root / name).is_file():
            raise RuntimeError(
                "Windows açılış kontrolü kullanıcı dosyasını üretmedi: " + name
            )
    after = {
        path.relative_to(executable.parent) for path in executable.parent.rglob("*")
    }
    if before != after:
        raise RuntimeError("Windows paketi uygulama klasörüne kullanıcı dosyası yazdı.")


def verify_installer(installer: Path) -> None:
    """Install, launch and uninstall in temporary folders, preserving user data."""
    with TemporaryDirectory(prefix="izlek-windows-install-") as temporary:
        root = Path(temporary)
        installed = root / "application"
        run(
            [
                str(installer),
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                "/SP-",
                f"/DIR={installed}",
                f"/LOG={root / 'setup.log'}",
            ]
        )
        smoke(validate_bundle(installed), root / "user", native=True)
        run(
            [
                str(installed / "unins000.exe"),
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
            ]
        )
        deadline = time.monotonic() + 20
        while (installed / "izlek.exe").exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        if (installed / "izlek.exe").exists():
            raise RuntimeError("Windows kaldırma kontrolü uygulamayı kaldıramadı.")
        if not (root / "user/data/izlek/izlek.sqlite3").is_file():
            raise RuntimeError("Kaldırıcı kişisel veritabanını sildi.")


def build(compiler: Path) -> Path:
    """Build only from the app spec; development data/docs never enter the EXE."""
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--distpath",
            str(OUTPUT),
            "--workpath",
            str(PROJECT_ROOT / "build/windows"),
            str(SPEC),
        ]
    )
    with TemporaryDirectory(prefix="izlek-windows-smoke-") as temporary:
        smoke(validate_bundle(BUNDLE), Path(temporary))
    version = project_version()
    run(
        [
            str(compiler),
            f"/DAppVersion={version}",
            f"/DBundleDir={BUNDLE}",
            f"/DOutputPath={OUTPUT}",
            str(INSTALLER_SCRIPT),
        ]
    )
    installer = OUTPUT / f"Izlek-{version}-windows-x64-setup.exe"
    if not installer.is_file():
        raise RuntimeError("Windows kurulum EXE dosyası oluşturulamadı.")
    verify_installer(installer)
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    installer.with_suffix(".exe.sha256").write_text(
        f"{digest}  {installer.name}\n", encoding="utf-8", newline="\n"
    )
    return installer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iscc", type=Path, help="Inno Setup ISCC.exe yolu")
    arguments = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Windows EXE yalnız Windows üzerinde üretilebilir.")
    if struct.calcsize("P") != 8 or platform.machine().lower() not in {
        "amd64",
        "x86_64",
    }:
        parser.error("64 bit x64 Python gereklidir.")
    compiler = arguments.iscc or shutil.which("ISCC.exe")
    if not compiler:
        parser.error("Inno Setup kurun veya --iscc ile ISCC.exe yolunu verin.")
    installer = build(Path(compiler).resolve())
    print("Windows kurulum paketi hazır:", installer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
