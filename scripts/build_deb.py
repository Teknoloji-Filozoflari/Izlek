"""Build a self-contained Debian/Ubuntu package from the PyInstaller bundle."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tomllib
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_FILE = PROJECT_ROOT / "packaging/izlek.spec"
CONTROL_TEMPLATE = PROJECT_ROOT / "packaging/debian/control.in"
ONEDIR = PROJECT_ROOT / "dist/izlek"

_DEBIAN_ARCHITECTURES = {"x86_64": "amd64", "aarch64": "arm64"}


def package_version() -> str:
    """Translate the PEP 440 development version to Debian ordering syntax."""
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    return project["project"]["version"].replace(".dev", "~dev")


def debian_architecture() -> str:
    """Return the Debian architecture corresponding to the PyInstaller host."""
    try:
        return _DEBIAN_ARCHITECTURES[platform.machine().lower()]
    except KeyError as error:
        raise RuntimeError(
            f"Desteklenmeyen Debian mimarisi: {platform.machine()}"
        ) from error


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def build_onedir() -> None:
    """Build the verified application payload without creating an AppDir."""
    if find_spec("PyInstaller") is None:
        raise RuntimeError("PyInstaller bulunamadı; önce -e '.[package]' kurun.")
    run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(SPEC_FILE)])
    if not (ONEDIR / "izlek").is_file():
        raise RuntimeError("PyInstaller one-folder çıktısı oluşturulamadı.")


def write_launcher(destination: Path) -> None:
    destination.write_text(
        "#!/bin/sh\nexec /usr/lib/izlek/izlek \"$@\"\n", encoding="utf-8"
    )
    destination.chmod(0o755)


def stage_package(
    root: Path,
    version: str,
    architecture: str,
    *,
    homepage: str,
    maintainer: str,
) -> Path:
    """Create the FHS-shaped package tree without writing to the host system."""
    package_root = root / "izlek"
    for directory in (
        "usr/bin",
        "usr/share/applications",
        "usr/share/icons/hicolor/scalable/apps",
        "usr/share/doc/izlek",
    ):
        (package_root / directory).mkdir(parents=True, exist_ok=True)
    shutil.copytree(ONEDIR, package_root / "usr/lib/izlek")
    write_launcher(package_root / "usr/bin/izlek")

    desktop = PROJECT_ROOT / "src/izlek/resources/desktop/izlek.desktop"
    icon = PROJECT_ROOT / "src/izlek/resources/icons/izlek.svg"
    shutil.copy2(desktop, package_root / "usr/share/applications/izlek.desktop")
    shutil.copy2(
        icon, package_root / "usr/share/icons/hicolor/scalable/apps/izlek.svg"
    )
    copyright_text = (
        PROJECT_ROOT / "packaging/debian/copyright"
    ).read_text(encoding="utf-8").replace("@HOMEPAGE@", homepage)
    (package_root / "usr/share/doc/izlek/copyright").write_text(
        copyright_text, encoding="utf-8"
    )

    control = CONTROL_TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "@VERSION@": version,
        "@ARCHITECTURE@": architecture,
        "@HOMEPAGE@": homepage,
        "@MAINTAINER@": maintainer,
    }
    for placeholder, value in replacements.items():
        control = control.replace(placeholder, value)
    control_target = package_root / "DEBIAN/control"
    control_target.parent.mkdir(parents=True, exist_ok=True)
    control_target.write_text(control, encoding="utf-8")
    return package_root


def build_deb(output: Path, *, homepage: str, maintainer: str) -> Path:
    """Build the `.deb` after staging it in a temporary, host-isolated tree."""
    version = package_version()
    architecture = debian_architecture()
    with TemporaryDirectory(prefix="izlek-deb-") as temporary:
        staged = stage_package(
            Path(temporary),
            version,
            architecture,
            homepage=homepage,
            maintainer=maintainer,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        run(["dpkg-deb", "--root-owner-group", "--build", str(staged), str(output)])
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-onedir-build",
        action="store_true",
        help="Mevcut dist/izlek one-folder çıktısını tekrar üretmeden paketle.",
    )
    parser.add_argument("--output", type=Path, help="Çıktı .deb yolu.")
    parser.add_argument(
        "--homepage",
        default=os.environ.get("IZLEK_HOMEPAGE"),
        help="Paketin gerçek upstream HTTPS adresi (veya IZLEK_HOMEPAGE).",
    )
    parser.add_argument(
        "--maintainer",
        default=os.environ.get("IZLEK_MAINTAINER"),
        help="Debian maintainer alanı (veya IZLEK_MAINTAINER).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.homepage or not args.homepage.startswith("https://"):
        print("Gerçek HTTPS homepage --homepage ile verilmelidir.", file=sys.stderr)
        return 2
    if (
        not args.maintainer
        or "<" not in args.maintainer
        or ">" not in args.maintainer
    ):
        print("Geçerli maintainer --maintainer ile verilmelidir.", file=sys.stderr)
        return 2
    if shutil.which("dpkg-deb") is None:
        print(
            "dpkg-deb bulunamadı; Debian/Ubuntu build ortamı gerekir.",
            file=sys.stderr,
        )
        return 2
    if not args.skip_onedir_build:
        build_onedir()
    if not (ONEDIR / "izlek").is_file():
        print("dist/izlek one-folder çıktısı bulunamadı.", file=sys.stderr)
        return 2
    output = args.output or (
        PROJECT_ROOT / f"dist/izlek_{package_version()}_{debian_architecture()}.deb"
    )
    result = build_deb(
        output.resolve(), homepage=args.homepage, maintainer=args.maintainer
    )
    print(f"Debian paketi hazır: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
