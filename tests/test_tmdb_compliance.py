"""Regression coverage for required visible TMDB and JustWatch attribution."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_about_screen_separates_tmdb_content_from_local_tracking_data():
    settings = (
        PROJECT_ROOT / "src/izlek/ui/qml/pages/SettingsPage.qml"
    ).read_text(encoding="utf-8")

    assert "tmdbAttributionNotice" in settings
    notice = "This product uses the TMDB API but is not endorsed or certified by TMDB."
    assert notice in settings
    assert "yalnızca İzlek'in yerel verisidir" in settings
    assert "justWatchAttributionLabel" in settings


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
    assert "İzleme seçenekleri JustWatch tarafından sağlanır" in providers
