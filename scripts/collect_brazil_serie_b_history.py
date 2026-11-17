"""Explicitly gated command-line entry point for the fixed Brazil Serie B import."""
from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import os
from urllib.parse import urlsplit

from app.providers.historical_import import (
    BOUNDARY_END,
    BOUNDARY_START,
    REQUEST_BUDGET,
    run_brazil_serie_b_historical_import,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Confirm a live provider import; also requires the environment kill-switch.",
    )
    parser.add_argument(
        "--start-at",
        default=BOUNDARY_START.isoformat(),
        help="Inclusive timezone-aware ISO-8601 collection boundary (UTC recommended).",
    )
    parser.add_argument(
        "--end-at",
        default=BOUNDARY_END.isoformat(),
        help="Exclusive timezone-aware ISO-8601 collection boundary (UTC recommended).",
    )
    parser.add_argument(
        "--request-budget",
        type=int,
        default=REQUEST_BUDGET,
        help=f"Hard request ceiling for this run (maximum {REQUEST_BUDGET}).",
    )
    parser.add_argument(
        "--resume-run-id",
        type=int,
        default=None,
        help="Resume a previously PAUSED import run without resetting its request ledger.",
    )
    args = parser.parse_args()

    database_url = (
        os.getenv("VELTRIX_AI_ANALYST_DATABASE_URL")
        or os.getenv("DATABASE_URL", "")
    ).strip()
    expected_database = os.getenv("EXPECTED_DATABASE_NAME", "")
    api_key = os.getenv("FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY", "")
    if not database_url or not expected_database:
        parser.error("dedicated database URL and EXPECTED_DATABASE_NAME are required")
    if expected_database != "veltrix_ai_analyst":
        parser.error("EXPECTED_DATABASE_NAME must be veltrix_ai_analyst")
    if urlsplit(database_url).path.lstrip("/").split("?", 1)[0] != expected_database:
        parser.error("database URL path does not match EXPECTED_DATABASE_NAME")
    if not args.execute:
        parser.error("--execute is required; no provider request was made")
    if os.getenv("VELTRIX_ENABLE_HISTORICAL_COLLECTION") != "true":
        parser.error("VELTRIX_ENABLE_HISTORICAL_COLLECTION=true is required")

    try:
        boundary_start = datetime.fromisoformat(args.start_at.replace("Z", "+00:00"))
        boundary_end = datetime.fromisoformat(args.end_at.replace("Z", "+00:00"))
    except ValueError:
        parser.error("--start-at and --end-at must be valid ISO-8601 timestamps")
    if (
        boundary_start.tzinfo is None
        or boundary_start.utcoffset() is None
        or boundary_end.tzinfo is None
        or boundary_end.utcoffset() is None
    ):
        parser.error("--start-at and --end-at must include a timezone offset")

    run_id = asyncio.run(
        run_brazil_serie_b_historical_import(
            database_url,
            api_key=api_key,
            execute=True,
            import_run_id=args.resume_run_id,
            boundary_start=boundary_start.astimezone(UTC),
            boundary_end=boundary_end.astimezone(UTC),
            request_budget=args.request_budget,
        )
    )
    print(f"HISTORICAL_IMPORT_FINISHED:run_id={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
