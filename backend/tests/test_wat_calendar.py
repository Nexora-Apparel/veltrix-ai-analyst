from datetime import UTC, datetime

import pytest

from app.wat_calendar import wat_day_window_utc


def test_wat_window_spans_previous_utc_date_at_midnight():
    start, end = wat_day_window_utc(datetime(2026, 11, 23, 0, 0, tzinfo=UTC))
    assert start == datetime(2026, 11, 22, 23, 0, tzinfo=UTC)
    assert end == datetime(2026, 11, 23, 23, 0, tzinfo=UTC)


def test_wat_window_is_stable_across_utc_midnight_within_same_wat_day():
    first = wat_day_window_utc(datetime(2026, 11, 23, 0, 30, tzinfo=UTC))
    second = wat_day_window_utc(datetime(2026, 11, 23, 22, 59, tzinfo=UTC))
    assert first == second


def test_wat_window_rolls_at_2300_utc():
    before = wat_day_window_utc(datetime(2026, 11, 23, 22, 59, 59, tzinfo=UTC))
    after = wat_day_window_utc(datetime(2026, 11, 23, 23, 0, tzinfo=UTC))
    assert before[0] == datetime(2026, 11, 22, 23, 0, tzinfo=UTC)
    assert after[0] == datetime(2026, 11, 23, 23, 0, tzinfo=UTC)


def test_wat_window_rejects_naive_datetime():
    with pytest.raises(ValueError, match="NOW_MUST_BE_TIMEZONE_AWARE"):
        wat_day_window_utc(datetime(2026, 11, 23, 12, 0))


def test_published_and_research_daily_queries_use_inclusive_exclusive_wat_bounds():
    import inspect
    from app.routes.public_predictions import _load_public_predictions
    from app.routes.research_predictions import _RESEARCH_QUERY

    published_loader = inspect.getsource(_load_public_predictions)
    assert "fixture.kickoff_at >= %s" in published_loader
    assert "fixture.kickoff_at < %s" in published_loader
    assert "fixture.kickoff_at > %s" not in published_loader
    assert "fixture.kickoff_at >= %s" in _RESEARCH_QUERY
    assert "fixture.kickoff_at < %s" in _RESEARCH_QUERY
    assert "fixture.kickoff_at > %s" not in _RESEARCH_QUERY
