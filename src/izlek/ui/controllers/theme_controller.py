"""Persist and expose the dark/light appearance preference."""

from PySide6.QtCore import Property, QObject, QSettings, Signal, Slot

_VALID = frozenset({"dark", "light"})


class ThemeController(QObject):
    """Keep Theme.qml mode in sync with QSettings without touching tokens."""

    changed = Signal()

    def __init__(
        self,
        settings: QSettings | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        mode = "dark"
        if settings is not None:
            stored = settings.value("appearance/theme", "dark")
            if isinstance(stored, str) and stored in _VALID:
                mode = stored
        self._mode = mode

    @Property(str, notify=changed)
    def mode(self) -> str:
        return self._mode

    @Property(bool, notify=changed)
    def isLight(self) -> bool:
        return self._mode == "light"

    @Slot(str)
    def setMode(self, mode: str) -> None:
        if mode not in _VALID or mode == self._mode:
            return
        self._mode = mode
        if self._settings is not None:
            self._settings.setValue("appearance/theme", mode)
            self._settings.sync()
        self.changed.emit()

    @Slot(int)
    def setModeIndex(self, index: int) -> None:
        self.setMode("light" if index == 1 else "dark")
