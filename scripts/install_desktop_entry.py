"""Install the development launcher and icon in the user's XDG data directory."""

import sys
from importlib.resources import files
from pathlib import Path

from izlek.core.paths import app_paths


def main() -> int:
    launcher = Path(sys.executable).parent / "izlek"
    if not launcher.is_file():
        print(
            "Önce bu Python ortamına İzlek paketini kurun: pip install -e .",
            file=sys.stderr,
        )
        return 1

    data_home = app_paths().data.parent
    desktop_target = data_home / "applications/izlek.desktop"
    icon_target = data_home / "icons/hicolor/scalable/apps/izlek.svg"
    if desktop_target.exists() and "X-Izlek-Development=true" not in (
        desktop_target.read_text(encoding="utf-8")
    ):
        print(f"Mevcut masaüstü kaydı korunuyor: {desktop_target}", file=sys.stderr)
        return 1

    package_files = files("izlek")
    desktop_source = package_files.joinpath("resources/desktop/izlek.desktop")
    icon_source = package_files.joinpath("resources/icons/izlek.svg")
    desktop_text = desktop_source.read_text(encoding="utf-8")
    # Desktop Entry Exec syntax requires quotes around paths containing spaces.
    escaped_path = str(launcher).replace("\\", "\\\\").replace('"', '\\"')
    escaped_path = escaped_path.replace("$", "\\$").replace("`", "\\`")
    command = f'"{escaped_path.replace("%", "%%")}"'
    desktop_text = desktop_text.replace("Exec=izlek\n", f"Exec={command}\n")
    desktop_text += "X-Izlek-Development=true\n"

    desktop_target.parent.mkdir(parents=True, exist_ok=True)
    icon_target.parent.mkdir(parents=True, exist_ok=True)
    desktop_target.write_text(desktop_text, encoding="utf-8")
    icon_target.write_bytes(icon_source.read_bytes())
    print(f"Masaüstü kaydı: {desktop_target}")
    print(f"Uygulama simgesi: {icon_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
