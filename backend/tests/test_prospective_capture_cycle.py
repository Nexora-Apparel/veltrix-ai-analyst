from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.providers.prospective_capture_cycle import completed_prospective_capture_run_ids


class FakeResult:
    def __init__(self, rows: list[tuple[int]]) -> None:
        self.rows = rows

    def fetchall(self) -> list[tuple[int]]:
        return self.rows


class FakeConnection:
    def __init__(self, rows: list[tuple[int]]) -> None:
        self.rows = rows
        self.query: str | None = None
        self.params: tuple[object, ...] | None = None

    def execute(self, query: str, params: tuple[object, ...]) -> FakeResult:
        self.query = query
        self.params = params
        return FakeResult(self.rows)


def test_daily_capture_lookup_uses_utc_day_not_rolling_window() -> None:
    connection = FakeConnection([(81,), (72,)])
    local_time = datetime(2026, 11, 25, 15, 30, tzinfo=timezone(timedelta(hours=1)))

    result = completed_prospective_capture_run_ids(
        connection, competition_id="522514093", utc_day=local_time
    )

    assert result == (81, 72)
    assert connection.params == (
        "5DollarFootballAPI",
        "5dollarfootballapi",
        "522514093",
        datetime(2026, 11, 25, tzinfo=UTC),
        datetime(2026, 11, 26, tzinfo=UTC),
    )
    assert connection.query is not None
    assert "finished_at >= %s" in connection.query
    assert "finished_at < %s" in connection.query
    assert "boundary_start" not in connection.query
    assert "boundary_end" not in connection.query


def test_daily_capture_lookup_rejects_naive_utc_day() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        completed_prospective_capture_run_ids(
            FakeConnection([]),
            competition_id="522514093",
            utc_day=datetime(2026, 11, 25),
        )


def test_daily_capture_lookup_returns_empty_when_no_cycle_completed_today() -> None:
    connection = FakeConnection([])
    result = completed_prospective_capture_run_ids(
        connection,
        competition_id="522514093",
        utc_day=datetime(2026, 11, 25, 10, tzinfo=UTC),
    )
    assert result == ()
