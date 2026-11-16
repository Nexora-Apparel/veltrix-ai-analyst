"""Checksum-verified PostgreSQL SQL migration runner."""
from __future__ import annotations

import hashlib
from pathlib import Path

import psycopg


class MigrationError(RuntimeError):
    """Raised when a migration cannot be safely applied."""


DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def apply_migrations(
    database_url: str,
    *,
    expected_database: str,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
) -> list[str]:
    """Apply ordered SQL migrations exactly once and reject target/checksum drift."""
    if not database_url.strip():
        raise MigrationError("DATABASE_URL_REQUIRED")
    if not expected_database.strip():
        raise MigrationError("EXPECTED_DATABASE_NAME_REQUIRED")
    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        raise MigrationError("NO_SQL_MIGRATIONS_FOUND")

    applied: list[str] = []
    with psycopg.connect(database_url) as connection:
        if connection.info.dbname != expected_database:
            raise MigrationError("DATABASE_TARGET_NAME_MISMATCH")
        if connection.info.dbname in {"veltrix-football", "veltrix_football"}:
            raise MigrationError("LEGACY_DATABASE_WRITES_DISABLED")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                version TEXT PRIMARY KEY,
                checksum CHAR(64) NOT NULL
                    CHECK (checksum ~ '^[0-9a-f]{64}$'),
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        connection.commit()

        for migration_path in migration_files:
            raw_sql = migration_path.read_bytes()
            checksum = hashlib.sha256(raw_sql).hexdigest()
            version = migration_path.name
            with connection.transaction():
                existing = connection.execute(
                    "SELECT checksum FROM public.schema_migrations WHERE version = %s",
                    (version,),
                ).fetchone()
                if existing is not None:
                    if str(existing[0]).strip() != checksum:
                        raise MigrationError(f"MIGRATION_CHECKSUM_DRIFT:{version}")
                    continue

                try:
                    connection.execute(raw_sql.decode("utf-8"), prepare=False)
                except (UnicodeDecodeError, psycopg.Error) as exc:
                    raise MigrationError(
                        f"MIGRATION_APPLY_FAILED:{version}:{type(exc).__name__}"
                    ) from None
                connection.execute(
                    """
                    INSERT INTO public.schema_migrations(version, checksum)
                    VALUES (%s, %s)
                    """,
                    (version, checksum),
                )
                applied.append(version)

    return applied
