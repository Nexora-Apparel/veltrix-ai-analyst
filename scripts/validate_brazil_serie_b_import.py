"""Run the read-only quality gate for a completed Brazil Serie B import."""
from __future__ import annotations

import argparse
import json
import os
from urllib.parse import urlsplit

import psycopg

from app.providers.historical_import import EXPECTED_DATABASE_NAME
from app.providers.historical_validation import validate_brazil_serie_b_import


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args()

    database_url = (
        os.getenv("VELTRIX_AI_ANALYST_DATABASE_URL")
        or os.getenv("DATABASE_URL", "")
    ).strip()
    expected_database = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not database_url or expected_database != EXPECTED_DATABASE_NAME:
        parser.error("dedicated database URL and exact expected database name are required")
    if urlsplit(database_url).path.lstrip("/").split("?", 1)[0] != expected_database:
        parser.error("database URL path does not match EXPECTED_DATABASE_NAME")

    with psycopg.connect(database_url) as connection:
        report = validate_brazil_serie_b_import(connection, args.run_id)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
