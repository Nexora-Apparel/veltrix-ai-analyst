from datetime import UTC, datetime

from app.wat_calendar import wat_day_window_utc


def test_wat_day_window_uses_lagos_midnight_boundaries():
    start, end = wat_day_window_utc(datetime(2026, 11, 26, 8, 0, tzinfo=UTC))
    assert start == datetime(2026, 11, 25, 23, 0, tzinfo=UTC)
    assert end == datetime(2026, 11, 26, 23, 0, tzinfo=UTC)


def test_wat_day_window_is_start_inclusive_and_end_exclusive():
    start, end = wat_day_window_utc(datetime(2026, 11, 26, 23, 0, tzinfo=UTC))
    assert start == datetime(2026, 11, 26, 23, 0, tzinfo=UTC)
    assert end == datetime(2026, 11, 27, 23, 0, tzinfo=UTC)


def test_wat_day_window_rejects_naive_datetime():
    try:
        wat_day_window_utc(datetime(2026, 11, 26, 8, 0))
    except ValueError as exc:
        assert str(exc) == "REFERENCE_MUST_BE_TIMEZONE_AWARE"
    else:
        raise AssertionError("naive datetime must be rejected")
