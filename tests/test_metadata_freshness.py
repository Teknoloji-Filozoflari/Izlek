"""Shared metadata freshness boundary behavior."""

from datetime import UTC, datetime, timedelta, timezone

from izlek.services.metadata_freshness import metadata_is_fresh


def test_metadata_is_fresh_for_at_most_24_hours():
    now = datetime(2026, 10, 3, 12, 0)

    assert metadata_is_fresh(now, now=now)
    assert metadata_is_fresh(now - timedelta(hours=24), now=now)
    assert not metadata_is_fresh(
        now - timedelta(hours=24, microseconds=1), now=now
    )
    assert not metadata_is_fresh(None, now=now)


def test_metadata_freshness_normalizes_aware_utc_values():
    now = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)

    assert metadata_is_fresh(now - timedelta(hours=1), now=now)


def test_metadata_freshness_compares_different_timezone_offsets():
    now = datetime(2026, 10, 3, 15, 0, tzinfo=timezone(timedelta(hours=3)))
    same_instant = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)

    assert metadata_is_fresh(same_instant - timedelta(hours=24), now=now)
    assert not metadata_is_fresh(
        same_instant - timedelta(hours=24, microseconds=1), now=now
    )
