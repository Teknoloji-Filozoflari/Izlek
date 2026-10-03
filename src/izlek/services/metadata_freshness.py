"""Shared 24-hour freshness decisions for locally cached TMDb metadata."""

from datetime import UTC, datetime, timedelta

METADATA_MAX_AGE = timedelta(hours=24)


def metadata_is_fresh(
    last_synced_at: datetime | None,
    *,
    now: datetime | None = None,
) -> bool:
    """Return true until a successful sync is more than 24 hours old."""
    if last_synced_at is None:
        return False
    current = now or datetime.now(UTC).replace(tzinfo=None)
    if current.tzinfo is not None:
        current = current.astimezone(UTC).replace(tzinfo=None)
    synced = last_synced_at
    if synced.tzinfo is not None:
        synced = synced.astimezone(UTC).replace(tzinfo=None)
    return synced >= current - METADATA_MAX_AGE
