"""Locale packs, catalog API, and Settings language picker."""

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt, QTimer
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.i18n import (
    AVAILABLE_LOCALES,
    DEFAULT_LOCALE,
    get_locale,
    set_locale,
    t,
    tmdb_language,
)
from izlek.i18n.catalog import catalog_keys
from izlek.security.token_store import StoredToken
from izlek.ui.controllers.locale_controller import LocaleController
from izlek.ui.controllers.token_controller import TokenController

LOCALES_DIR = Path(__file__).resolve().parents[1] / "src/izlek/i18n/locales"


class ExistingTokenStore:
    def load(self):
        return StoredToken("test-only", "keyring")


def test_all_locale_packs_exist_and_share_keys():
    expected = catalog_keys(DEFAULT_LOCALE)
    assert expected
    assert "nav.settings" in expected
    assert "settings.language" in expected
    for code in AVAILABLE_LOCALES:
        path = LOCALES_DIR / f"{code}.json"
        assert path.is_file(), code
        assert catalog_keys(code) == expected, code


def test_translate_switches_locale_and_falls_back():
    set_locale("tr")
    assert t("nav.settings") == "Ayarlar"
    assert tmdb_language() == "tr-TR"
    set_locale("en")
    assert get_locale() == "en"
    assert t("nav.settings") == "Settings"
    assert tmdb_language() == "en-US"
    set_locale("az")
    assert t("nav.home") == "Ana səhifə"
    set_locale("kk")
    assert tmdb_language() == "kk-KZ"
    assert t("missing.key.does.not.exist") == "missing.key.does.not.exist"
    set_locale("tr")


@pytest.mark.parametrize("code", AVAILABLE_LOCALES)
def test_each_locale_has_native_name_and_tmdb(code):
    set_locale(code)
    assert t("app.name")
    assert t("settings.language")
    assert "-" in tmdb_language(code)
    set_locale(DEFAULT_LOCALE)


def test_locale_controller_persists_choice(tmp_path):
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    controller = LocaleController(settings=settings)
    assert controller.locale == DEFAULT_LOCALE
    assert len(controller.availableLocales) == len(AVAILABLE_LOCALES)
    controller.setLocale("es")
    assert controller.locale == "es"
    assert controller.t("nav.settings") == "Ajustes"
    assert settings.value("ui/locale") == "es"
    again = LocaleController(settings=settings)
    assert again.locale == "es"
    set_locale(DEFAULT_LOCALE)


def test_settings_language_picker_switches_ui(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    set_locale(DEFAULT_LOCALE)
    token = TokenController(store=ExistingTokenStore())
    prefs = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    locale = LocaleController(settings=prefs)
    application, _engine, window = create_application(
        token_controller=token, locale_controller=locale
    )
    assert window.findChild(QQuickItem, "navSettings").property("label") == "Ayarlar"

    item = window.findChild(QQuickItem, "navSettings")
    center = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    QTest.mouseClick(
        window,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(int(center.x()), int(center.y())),
    )
    application.processEvents()
    assert window.property("currentIndex") == 5
    stack = window.findChild(QQuickItem, "contentStack")
    assert stack.property("currentItem").property("pageTitle") == "Ayarlar"
    picker = window.findChild(QQuickItem, "languagePicker")
    assert picker is not None
    assert window.findChild(QQuickItem, "languageSettingsCard") is not None

    locale.setLocale("en")
    application.processEvents()
    assert window.findChild(QQuickItem, "navSettings").property("label") == "Settings"
    assert stack.property("currentItem").property("pageTitle") == "Settings"
    assert locale.t("settings.language") == "Language"

    QTimer.singleShot(0, application.quit)
    assert application.exec() == 0
    set_locale(DEFAULT_LOCALE)
