"""Explicitly gated command-line entry point for the fixed Brazil Serie B import."""
from __future__ import annotations

import argparse
import asyncio
import os
from urllib.parse import urlsplit

from app.providers.historical_import import run_brazil_serie_b_historical_import


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Confirm a live provider import; also requires the environment kill-switch.",
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

    run_id = asyncio.run(
        run_brazil_serie_b_historical_import(
            database_url,
            api_key=api_key,
            execute=True,
            import_run_id=args.resume_run_id,
        )
    )
    print(f"HISTORICAL_IMPORT_FINISHED:run_id={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
