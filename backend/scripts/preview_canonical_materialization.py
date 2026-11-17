"""Run a read-only production preview of the pinned canonical materialization scope."""
from __future__ import annotations

import json
import os
import sys

import psycopg

from app.canonicalization import build_brazil_serie_b_materialization_plan


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    expected_database = os.environ.get("EXPECTED_DATABASE_NAME", "")
    if not database_url or expected_database != "veltrix_ai_analyst":
        raise SystemExit("CANONICAL_PREVIEW_DATABASE_CONFIGURATION_INVALID")

    # Enforce read-only mode at connection and transaction levels.
    with psycopg.connect(
        database_url,
        options="-c default_transaction_read_only=on",
    ) as connection:
        if connection.info.dbname != expected_database:
            raise SystemExit("CANONICAL_PREVIEW_DATABASE_TARGET_MISMATCH")
        with connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            plan = build_brazil_serie_b_materialization_plan(connection)
            print(json.dumps(plan.as_dict(), sort_keys=True, default=str))
            if not plan.ready:
                print("CANONICAL_MATERIALIZATION_PLAN_BLOCKED", file=sys.stderr)
                return 2
            print("CANONICAL_MATERIALIZATION_PLAN_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
