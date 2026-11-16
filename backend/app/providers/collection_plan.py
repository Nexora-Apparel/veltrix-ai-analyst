"""Deterministic half-open UTC date windows for bounded provider collection."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class DateWindow:
    """A half-open UTC interval: start_at <= event_time < end_at."""

    start_at: datetime
    end_at: datetime

    def __post_init__(self) -> None:
        for field_name, value in (("start_at", self.start_at), ("end_at", self.end_at)):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be later than start_at")


def build_date_windows(
    start_at: datetime,
    end_at: datetime,
    *,
    window_days: int = 7,
) -> tuple[DateWindow, ...]:
    """Split an interval into contiguous, non-overlapping UTC windows.

    The final window is clipped to end_at. All windows use half-open
    boundaries so adjacent requests cannot double-count boundary timestamps.
    This helper performs no provider requests and enforces no persistence.
    """
    if start_at.tzinfo is None or start_at.utcoffset() is None:
        raise ValueError("start_at must be timezone-aware")
    if end_at.tzinfo is None or end_at.utcoffset() is None:
        raise ValueError("end_at must be timezone-aware")
    if isinstance(window_days, bool) or not isinstance(window_days, int) or window_days <= 0:
        raise ValueError("window_days must be a positive integer")

    start = start_at.astimezone(UTC)
    end = end_at.astimezone(UTC)
    if end <= start:
        raise ValueError("end_at must be later than start_at")

    width = timedelta(days=window_days)
    windows: list[DateWindow] = []
    cursor = start
    while cursor < end:
        boundary = min(cursor + width, end)
        windows.append(DateWindow(start_at=cursor, end_at=boundary))
        cursor = boundary

    return tuple(windows)