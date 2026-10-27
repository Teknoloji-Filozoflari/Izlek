"""Persist and expose the UI language to QML."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QObject, QSettings, Signal, Slot

from izlek.core.paths import app_paths
from izlek.i18n import (
    AVAILABLE_LOCALES,
    DEFAULT_LOCALE,
    available_locales,
    get_locale,
    set_locale,
    t,
    tmdb_language,
)


class LocaleController(QObject):
    """Settings-backed locale bridge: `i18n.t(key)` and language picker rows."""

    localeChanged = Signal()

    def __init__(
        self,
        settings: QSettings | None = None,
        settings_path: Path | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._revision = 0
        self._settings = settings
        if self._settings is None:
            path = settings_path
            if path is None:
                try:
                    config = app_paths().config
                    config.mkdir(mode=0o700, parents=True, exist_ok=True)
                    path = config / "preferences.ini"
                except OSError:
                    path = None
            if path is not None:
                self._settings = QSettings(str(path), QSettings.Format.IniFormat)
        stored = DEFAULT_LOCALE
        if self._settings is not None:
            stored = str(
                self._settings.value("ui/locale", DEFAULT_LOCALE, type=str)
                or DEFAULT_LOCALE
            )
        set_locale(stored)
        self._locale = get_locale()

    @Property(str, notify=localeChanged)
    def locale(self) -> str:
        return self._locale

    @Property(int, notify=localeChanged)
    def revision(self) -> int:
        """Bump when the language changes so QML bindings re-evaluate `t()`."""
        return self._revision

    @Property(str, notify=localeChanged)
    def tmdbLanguage(self) -> str:
        return tmdb_language(self._locale)

    @Property("QVariantList", notify=localeChanged)
    def availableLocales(self) -> list[dict[str, str]]:
        return available_locales()

    @Slot(str, result=str)
    def t(self, key: str) -> str:
        return t(key)

    @Slot(str, str, result=str)
    def tf(self, key: str, value: str) -> str:
        """One-argument format helper for simple `{name}` / `{size}` strings."""
        message = t(key)
        try:
            return message.format(
                name=value,
                title=value,
                size=value,
                version=value,
                noun=value,
                score=value,
                count=value,
                page=value,
                total=value,
                movies=value,
                shows=value,
                episodes=value,
            )
        except (KeyError, ValueError, IndexError):
            return message

    @Slot(str)
    def setLocale(self, code: str) -> None:
        normalized = set_locale(code)
        if normalized == self._locale:
            return
        self._locale = normalized
        self._revision += 1
        if self._settings is not None:
            self._settings.setValue("ui/locale", normalized)
            self._settings.sync()
        self.localeChanged.emit()

    @Slot(result=list)
    def supportedCodes(self) -> list[str]:
        return list(AVAILABLE_LOCALES)
