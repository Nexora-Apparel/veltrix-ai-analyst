"""Apply the repository's checksum-verified PostgreSQL migrations."""
from __future__ import annotations

import os

from app.db.migrations import MigrationError, apply_migrations


def main() -> int:
    database_url = os.getenv("DATABASE_URL", "")
    try:
        applied = apply_migrations(
            database_url,
            expected_database=os.getenv("EXPECTED_DATABASE_NAME", ""),
        )
    except MigrationError as exc:
        print(f"MIGRATION_FAILED:{exc}")
        return 1

    if applied:
        for version in applied:
            print(f"APPLIED:{version}")
    else:
        print("MIGRATIONS_UP_TO_DATE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
