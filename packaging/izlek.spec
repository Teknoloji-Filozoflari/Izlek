"""PyInstaller one-folder specification for the Linux desktop application."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata


PROJECT_ROOT = Path(SPECPATH).resolve().parent
SOURCE_ROOT = PROJECT_ROOT / "src"
PACKAGE_ROOT = SOURCE_ROOT / "izlek"

datas = copy_metadata("izlek")
datas += [
    (str(PACKAGE_ROOT / "ui/qml"), "izlek/ui/qml"),
    (str(PACKAGE_ROOT / "resources"), "izlek/resources"),
]
for migration in (PACKAGE_ROOT / "db/migrations").rglob("*.py"):
    destination = migration.parent.relative_to(SOURCE_ROOT)
    datas.append((str(migration), str(destination)))

hiddenimports = collect_submodules("keyring.backends")
hiddenimports += collect_submodules("sqlalchemy.dialects.sqlite")

analysis = Analysis(
    [str(PACKAGE_ROOT / "__main__.py")],
    pathex=[str(SOURCE_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="izlek",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="izlek",
)
