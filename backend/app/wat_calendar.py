"""Authoritative Nigeria/WAT calendar-day boundaries for fixture feeds."""
from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

WAT = ZoneInfo("Africa/Lagos")


def wat_day_window_utc(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return [WAT midnight, next WAT midnight) converted to UTC."""
    instant = now or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("NOW_MUST_BE_TIMEZONE_AWARE")
    local_day = instant.astimezone(WAT).date()
    start_local = datetime.combine(local_day, time.min, tzinfo=WAT)
    end_local = datetime.combine(local_day + timedelta(days=1), time.min, tzinfo=WAT)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)
