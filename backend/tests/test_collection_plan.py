from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.providers.collection_plan import DateWindow, build_date_windows


def test_brazil_serie_b_candidate_range_builds_34_contiguous_windows() -> None:
    start = datetime(2026, 3, 21, tzinfo=UTC)
    end = datetime(2026, 11, 9, tzinfo=UTC)

    windows = build_date_windows(start, end, window_days=7)

    assert len(windows) == 34
    assert windows[0] == DateWindow(start_at=start, end_at=start + timedelta(days=7))
    assert windows[-1].end_at == end
    assert all(window.end_at > window.start_at for window in windows)
    assert all(window.end_at - window.start_at <= timedelta(days=7) for window in windows)
    assert all(left.end_at == right.start_at for left, right in zip(windows, windows[1:]))


def test_windows_normalize_offsets_to_utc_and_clip_final_window() -> None:
    local_zone = timezone(timedelta(hours=3))
    start = datetime(2026, 1, 1, 3, tzinfo=local_zone)
    end = datetime(2026, 1, 10, 3, tzinfo=local_zone)

    windows = build_date_windows(start, end, window_days=7)

    assert windows[0].start_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert windows[-1].end_at == datetime(2026, 1, 10, tzinfo=UTC)
    assert windows[-1].end_at - windows[-1].start_at == timedelta(days=2)


@pytest.mark.parametrize(
    ("start", "end", "window_days"),
    [
        (datetime(2026, 1, 1), datetime(2026, 1, 2, tzinfo=UTC), 7),
        (datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2), 7),
        (datetime(2026, 1, 2, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC), 7),
        (datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC), 0),
        (datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC), -1),
        (datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC), True),
    ],
)
def test_invalid_window_inputs_are_rejected(
    start: datetime,
    end: datetime,
    window_days: int,
) -> None:
    with pytest.raises(ValueError):
        build_date_windows(start, end, window_days=window_days)


def test_date_window_rejects_empty_or_naive_interval() -> None:
    with pytest.raises(ValueError):
        DateWindow(
            start_at=datetime(2026, 1, 1, tzinfo=UTC),
            end_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    with pytest.raises(ValueError):
        DateWindow(
            start_at=datetime(2026, 1, 1),
            end_at=datetime(2026, 1, 2, tzinfo=UTC),
        )