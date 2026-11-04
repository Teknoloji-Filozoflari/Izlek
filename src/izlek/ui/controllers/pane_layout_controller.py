"""Persist user-resized multi-pane widths in window.ini."""

from PySide6.QtCore import QObject, QSettings, Slot

_KEY_PREFIX = "panes/"
_DEFAULTS: dict[str, int] = {
    "main_sidebar": 248,
    "discover_filters": 280,
    "lists_sidebar": 300,
    "library_filters": 280,
    "stats_charts": 480,
    "detail_lower": 420,
}
_MINIMUMS: dict[str, int] = {
    "main_sidebar": 180,
    "discover_filters": 220,
    "lists_sidebar": 220,
    "library_filters": 220,
    "stats_charts": 280,
    "detail_lower": 280,
}
_MAXIMUMS: dict[str, int] = {
    "main_sidebar": 360,
    "discover_filters": 420,
    "lists_sidebar": 480,
    "library_filters": 420,
    "stats_charts": 900,
    "detail_lower": 720,
}


def _clamp(key: str, value: int) -> int:
    low = _MINIMUMS.get(key, 160)
    high = _MAXIMUMS.get(key, 640)
    return max(low, min(high, int(value)))


class PaneLayoutController(QObject):
    """Expose named pane widths to QML and keep them in QSettings."""

    def __init__(
        self,
        settings: QSettings | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings

    @Slot(str, result=int)
    def defaultWidth(self, key: str) -> int:
        return _DEFAULTS.get(key, 280)

    @Slot(str, result=int)
    def minimumWidth(self, key: str) -> int:
        return _MINIMUMS.get(key, 160)

    @Slot(str, result=int)
    def maximumWidth(self, key: str) -> int:
        return _MAXIMUMS.get(key, 640)

    @Slot(str, int, result=int)
    def widthFor(self, key: str, default: int = 0) -> int:
        fallback = default if default > 0 else _DEFAULTS.get(key, 280)
        if self._settings is None:
            return _clamp(key, fallback)
        stored = self._settings.value(f"{_KEY_PREFIX}{key}", fallback)
        try:
            value = int(stored)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            value = int(fallback)
        return _clamp(key, value)

    @Slot(str, int)
    def setWidthFor(self, key: str, width: int) -> None:
        value = _clamp(key, width)
        if self._settings is None:
            return
        current = self._settings.value(f"{_KEY_PREFIX}{key}")
        try:
            if current is not None and int(current) == value:  # type: ignore[arg-type]
                return
        except (TypeError, ValueError):
            pass
        self._settings.setValue(f"{_KEY_PREFIX}{key}", value)
        self._settings.sync()
