"""Canonical Africa/Lagos calendar-day boundaries for UTC timestamp queries."""
from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

_WAT = ZoneInfo("Africa/Lagos")


def wat_day_window_utc(reference: datetime) -> tuple[datetime, datetime]:
    """Return the inclusive UTC start and exclusive UTC end of reference's WAT day."""
    if reference.tzinfo is None or reference.utcoffset() is None:
        raise ValueError("REFERENCE_MUST_BE_TIMEZONE_AWARE")
    local_day = reference.astimezone(_WAT).date()
    start_local = datetime.combine(local_day, time.min, tzinfo=_WAT)
    end_local = datetime.combine(local_day + timedelta(days=1), time.min, tzinfo=_WAT)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)
