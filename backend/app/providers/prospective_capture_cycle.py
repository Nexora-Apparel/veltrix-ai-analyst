"""Daily idempotency rules for prospective provider observation cycles."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

PROVIDER_NAME = "5DollarFootballAPI"
SOURCE_ID = "5dollarfootballapi"


def completed_prospective_capture_run_ids(
    connection: Any,
    *,
    competition_id: str,
    utc_day: datetime,
) -> tuple[int, ...]:
    """Return validated-cycle candidates completed within one UTC calendar day.

    Prospective captures intentionally reuse the same rolling fixture window
    every day. Their idempotency key is therefore the competition plus UTC day,
    not the rolling window boundaries. A previous day's completed import must
    not suppress today's fresh provider observation cycle.
    """
    if utc_day.tzinfo is None or utc_day.utcoffset() is None:
        raise ValueError("utc_day must be timezone-aware")

    day_start = utc_day.astimezone(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    next_day = day_start + timedelta(days=1)
    rows = connection.execute(
        """
        SELECT id
        FROM veltrix_ai_analyst.import_runs
        WHERE provider = %s
          AND source_id = %s
          AND scope_value = %s
          AND import_type = 'prospective_capture'
          AND status = 'COMPLETED'
          AND finished_at >= %s
          AND finished_at < %s
        ORDER BY finished_at DESC NULLS LAST, id DESC
        """,
        (PROVIDER_NAME, SOURCE_ID, competition_id, day_start, next_day),
    ).fetchall()
    return tuple(int(row[0]) for row in rows)
