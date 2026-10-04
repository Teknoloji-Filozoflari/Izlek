"""Build an RPM from the existing PyInstaller one-folder application."""

import argparse
import platform
import shutil
import subprocess
import tarfile
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory

if __package__:
    from .build_appimage import build_onedir, smoke
else:
    from build_appimage import build_onedir, smoke

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ONEDIR = PROJECT_ROOT / "dist/izlek"


def stage_source(destination: Path, version: str) -> Path:
    """Archive only the application bundle and public installation assets."""
    archive = destination / f"izlek-{version}.tar.gz"
    prefix = f"izlek-{version}"
    with tarfile.open(archive, "w:gz") as output:
        output.add(ONEDIR, arcname=f"{prefix}/payload")
        for source, name in (
            (PROJECT_ROOT / "LICENSE", "LICENSE"),
            (PROJECT_ROOT / "src/izlek/resources/icons/izlek.svg", "izlek.svg"),
            (
                PROJECT_ROOT / "src/izlek/resources/desktop/izlek.desktop",
                "izlek.desktop",
            ),
        ):
            output.add(source, arcname=f"{prefix}/{name}")
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-onedir-build", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "dist")
    args = parser.parse_args()
    architecture = platform.machine().lower()
    if architecture not in {"x86_64", "aarch64"}:
        parser.error(f"Desteklenmeyen RPM mimarisi: {architecture}")
    if shutil.which("rpmbuild") is None:
        parser.error("rpmbuild bulunamadı; önce RPM build araçlarını kurun.")
    if not args.skip_onedir_build:
        build_onedir()
    if not (ONEDIR / "izlek").is_file():
        parser.error("dist/izlek uygulama çıktısı bulunamadı.")
    smoke(ONEDIR / "izlek", immutable_root=ONEDIR)
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    version = project["project"]["version"]
    with TemporaryDirectory(prefix="izlek-rpmbuild-") as temporary:
        root = Path(temporary)
        for folder in ("BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"):
            (root / folder).mkdir()
        stage_source(root / "SOURCES", version)
        spec = root / "SPECS/izlek.spec"
        shutil.copy2(PROJECT_ROOT / "packaging/rpm/izlek.spec", spec)
        subprocess.run(
            [
                "rpmbuild", "-bb", "--define", f"_topdir {root}",
                "--define", f"izlek_version {version}",
                "--target", architecture, str(spec),
            ],
            check=True,
        )
        packages = list((root / "RPMS").rglob("izlek-*.rpm"))
        if not packages:
            raise RuntimeError("RPM çıktısı oluşturulamadı.")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for package in packages:
            target = args.output_dir / package.name
            shutil.copy2(package, target)
            print(f"RPM hazır: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
