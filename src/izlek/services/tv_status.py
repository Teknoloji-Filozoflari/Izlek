"""Rules for TV status derived from local episode progress."""

from dataclasses import dataclass

from izlek.db.models import TrackingStatus


@dataclass(frozen=True)
class TvProgress:
    """Known episode counts; unknown air dates are not treated as aired."""

    watched_count: int
    aired_count: int
    unwatched_aired_count: int
    missing_metadata_count: int

    @property
    def metadata_complete(self) -> bool:
        return self.missing_metadata_count == 0


def automatic_status(
    current: TrackingStatus | None,
    *,
    manual: bool,
    progress: TvProgress,
    explicit_unwatch: bool,
) -> TrackingStatus | None:
    """Apply progress actions while preserving manual and completed choices.

    Metadata refresh never calls this function. A new episode does not demote a
    completed show; only an explicit unwatch action may do that.
    """
    if manual:
        return current
    if progress.watched_count == 0:
        return None
    if (
        progress.metadata_complete
        and progress.aired_count > 0
        and progress.unwatched_aired_count == 0
    ):
        return TrackingStatus.WATCHED
    if current == TrackingStatus.WATCHED and not explicit_unwatch:
        return current
    return TrackingStatus.WATCHING
