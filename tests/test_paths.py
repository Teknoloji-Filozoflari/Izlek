"""XDG path behavior without touching the user's directories."""

from pathlib import Path

from izlek.core.paths import app_paths


def test_xdg_defaults(tmp_path: Path):
    paths = app_paths(env={}, home=tmp_path)
    assert paths.config == tmp_path / ".config/izlek"
    assert paths.data == tmp_path / ".local/share/izlek"
    assert paths.cache == tmp_path / ".cache/izlek"
    assert paths.logs == tmp_path / ".local/state/izlek/logs"
    assert not paths.logs.exists()


def test_absolute_overrides_and_relative_fallback(tmp_path: Path):
    paths = app_paths(
        env={
            "XDG_CONFIG_HOME": str(tmp_path / "settings"),
            "XDG_DATA_HOME": "relative/data",
            "XDG_CACHE_HOME": str(tmp_path / "images"),
            "XDG_STATE_HOME": str(tmp_path / "state"),
        },
        home=tmp_path,
    )
    assert paths.config == tmp_path / "settings/izlek"
    assert paths.data == tmp_path / ".local/share/izlek"
    assert paths.cache == tmp_path / "images/izlek"
    assert paths.logs == tmp_path / "state/izlek/logs"
