"""Explicitly gated, competition-scoped 5Dollar historical importer."""
from __future__ import annotations

import argparse
import asyncio
import os
from datetime import UTC, datetime
from urllib.parse import urlsplit

from app.providers.approvals import FIVEDOLLAR_COMMUNITY_APPROVAL
from app.providers.historical_import import (
    BOUNDARY_END,
    BOUNDARY_START,
    REQUEST_BUDGET,
    run_competition_historical_import,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition-id", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--start-at", default=BOUNDARY_START.isoformat())
    parser.add_argument("--end-at", default=BOUNDARY_END.isoformat())
    parser.add_argument("--request-budget", type=int, default=20)
    parser.add_argument("--resume-run-id", type=int, default=None)
    args = parser.parse_args()

    competition_id = args.competition_id.strip()
    if (
        not competition_id
        or competition_id not in FIVEDOLLAR_COMMUNITY_APPROVAL.scope_values
    ):
        parser.error("competition ID is not in the approved 5Dollar collection scope")
    database_url = (
        os.getenv("VELTRIX_AI_ANALYST_DATABASE_URL")
        or os.getenv("DATABASE_URL", "")
    ).strip()
    expected_database = os.getenv("EXPECTED_DATABASE_NAME", "")
    api_key = os.getenv("FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY", "")
    if not database_url or expected_database != "veltrix_ai_analyst":
        parser.error("dedicated veltrix_ai_analyst database configuration is required")
    if urlsplit(database_url).path.lstrip("/").split("?", 1)[0] != expected_database:
        parser.error("database URL path does not match EXPECTED_DATABASE_NAME")
    if not args.execute:
        parser.error("--execute is required; no provider request was made")
    if os.getenv("VELTRIX_ENABLE_HISTORICAL_COLLECTION") != "true":
        parser.error("VELTRIX_ENABLE_HISTORICAL_COLLECTION=true is required")
    try:
        start_at = datetime.fromisoformat(args.start_at)
        end_at = datetime.fromisoformat(args.end_at)
    except ValueError:
        parser.error("date boundaries must be valid ISO-8601 timestamps")
    if any(
        value.tzinfo is None or value.utcoffset() is None
        for value in (start_at, end_at)
    ):
        parser.error("date boundaries must include a timezone offset")
    if end_at <= start_at:
        parser.error("end-at must be later than start-at")
    if not 1 <= args.request_budget <= REQUEST_BUDGET:
        parser.error(f"request budget must be between 1 and {REQUEST_BUDGET}")

    run_id = asyncio.run(
        run_competition_historical_import(
            database_url,
            api_key=api_key,
            execute=True,
            import_run_id=args.resume_run_id,
            approval=FIVEDOLLAR_COMMUNITY_APPROVAL,
            boundary_start=start_at.astimezone(UTC),
            boundary_end=end_at.astimezone(UTC),
            request_budget=args.request_budget,
            competition_id=competition_id,
        )
    )
    print(f"HISTORICAL_IMPORT_FINISHED:competition_id={competition_id}:run_id={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
