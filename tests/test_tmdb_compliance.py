"""Regression coverage for required visible TMDB and JustWatch attribution."""

from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlExpression
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from izlek.app import create_application
from izlek.i18n import AVAILABLE_LOCALES, set_locale, t
from izlek.security.token_store import StoredToken
from izlek.ui.controllers.token_controller import TokenController

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTICE = "This product uses the TMDB API but is not endorsed or certified by TMDB."


def test_about_screen_separates_tmdb_content_from_local_tracking_data():
    settings = (
        PROJECT_ROOT / "src/izlek/ui/qml/pages/SettingsPage.qml"
    ).read_text(encoding="utf-8")

    assert "tmdbAttributionNotice" in settings
    assert "settings.tmdb_notice" in settings
    assert "settings.tmdb_data" in settings
    assert "justWatchAttributionLabel" in settings
    assert "watchRegionSettingsCard" in settings
    assert "metadataSourcesSettingsCard" in settings
    assert "omdbNonCommercialCheck" in settings
    set_locale("tr")
    assert t("settings.tmdb_notice") == NOTICE
    assert "yalnızca İzlek'in yerel verisidir" in t("settings.tmdb_data")
    for code in AVAILABLE_LOCALES:
        set_locale(code)
        assert t("settings.tmdb_notice") == NOTICE
    set_locale("tr")


def test_detail_and_provider_views_keep_their_remote_sources_visible():
    movie = (
        PROJECT_ROOT / "src/izlek/ui/qml/pages/MovieDetailPage.qml"
    ).read_text(encoding="utf-8")
    television = (
        PROJECT_ROOT / "src/izlek/ui/qml/pages/TvDetailPage.qml"
    ).read_text(encoding="utf-8")
    providers = (
        PROJECT_ROOT / "src/izlek/ui/qml/components/ProviderSection.qml"
    ).read_text(encoding="utf-8")

    assert "movieTmdbSourceLabel" in movie
    assert "tvTmdbSourceLabel" in television
    assert "provider.attribution" in providers
    set_locale("tr")
    assert "JustWatch" in t("provider.attribution")
    set_locale("tr")


def test_official_logo_loads_in_about_screen():
    class Store:
        def load(self):
            return StoredToken("test-only", "keyring")

    application, engine, window = create_application(
        token_controller=TokenController(store=Store())
    )
    try:
        window.navigate(5)
        QTest.qWait(300)
        logo = window.findChild(QQuickItem, "tmdbLogo")
        assert logo is not None
        status = QQmlExpression(engine.rootContext(), logo, "Number(status)")
        assert status.evaluate()[0] == 1  # Image.Ready
        assert logo.property("source").path().endswith("/images/tmdb.svg")
        assert logo.width() == 116 and logo.height() == 16
        assert window.findChild(QObject, "tmdbAttributionNotice") is not None
    finally:
        window.close()
        application.processEvents()
