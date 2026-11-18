"""Sequential, resumable batch collection for all approved 5Dollar competitions."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from urllib.parse import urlsplit

import psycopg

from app.providers.approvals import FIVEDOLLAR_COMMUNITY_APPROVAL
from app.providers.historical_import import (
    REQUEST_BUDGET,
    run_competition_historical_import,
)
from app.providers.historical_validation import validate_competition_import

COMPETITIONS = (
    ("3118717965", "Brazil Serie A"),
    ("4160026622", "England Premier League"),
    ("3614399544", "France Ligue 1"),
    ("686337048", "Germany Bundesliga I"),
    ("3405541143", "Italy Serie A"),
    ("4212821298", "Spain La Liga"),
)


def completed_run(database_url: str, competition_id: str, start_at: datetime, end_at: datetime):
    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            """
            SELECT id FROM veltrix_ai_analyst.import_runs
            WHERE scope_value = %s AND boundary_start = %s AND boundary_end = %s
              AND import_type = 'historical_backfill' AND status = 'COMPLETED'
            ORDER BY finished_at DESC NULLS LAST, id DESC
            """,
            (competition_id, start_at, end_at),
        ).fetchall()
        for (run_id,) in rows:
            try:
                report = validate_competition_import(connection, int(run_id), competition_id)
                return int(run_id), report
            except Exception:  # noqa: BLE001 - invalid historical runs are skipped so older valid runs can be checked
                continue
    return None


def resumable_run(database_url: str, competition_id: str, start_at: datetime, end_at: datetime):
    """Return the single matching open run and its original request budget."""
    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            """
            SELECT id, request_budget, requests_used, status
            FROM veltrix_ai_analyst.import_runs
            WHERE scope_value = %s AND boundary_start = %s AND boundary_end = %s
              AND import_type = 'historical_backfill'
              AND status IN ('PAUSED', 'RUNNING')
            ORDER BY id DESC
            """,
            (competition_id, start_at, end_at),
        ).fetchall()
    if len(rows) > 1:
        raise RuntimeError(
            f"MULTIPLE_OPEN_IMPORT_RUNS_FOR_COMPETITION:{competition_id}"
        )
    if not rows:
        return None
    run_id, request_budget, requests_used, status = rows[0]
    if int(requests_used) > int(request_budget):
        raise RuntimeError(f"OPEN_IMPORT_RUN_BUDGET_INTEGRITY_FAILURE:{run_id}")
    return int(run_id), int(request_budget), int(requests_used), str(status)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-at", required=True)
    parser.add_argument("--end-at", required=True)
    parser.add_argument("--request-budget", type=int, default=20)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    start_at = datetime.fromisoformat(args.start_at)
    end_at = datetime.fromisoformat(args.end_at)
    if any(v.tzinfo is None or v.utcoffset() is None for v in (start_at, end_at)):
        parser.error("date boundaries must include a timezone offset")
    start_at, end_at = start_at.astimezone(UTC), end_at.astimezone(UTC)
    if end_at <= start_at:
        parser.error("end-at must be later than start-at")
    if not 1 <= args.request_budget <= REQUEST_BUDGET:
        parser.error(f"request budget must be between 1 and {REQUEST_BUDGET}")
    if not args.execute:
        parser.error("--execute is required")
    if os.getenv("VELTRIX_ENABLE_HISTORICAL_COLLECTION") != "true":
        parser.error("VELTRIX_ENABLE_HISTORICAL_COLLECTION=true is required")

    database_url = (os.getenv("VELTRIX_AI_ANALYST_DATABASE_URL") or os.getenv("DATABASE_URL", "")).strip()
    expected_database = os.getenv("EXPECTED_DATABASE_NAME", "")
    api_key = os.getenv("FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY", "")
    if not database_url or expected_database != "veltrix_ai_analyst":
        parser.error("dedicated veltrix_ai_analyst database configuration is required")
    if urlsplit(database_url).path.lstrip("/").split("?", 1)[0] != expected_database:
        parser.error("database URL path does not match EXPECTED_DATABASE_NAME")
    if not api_key:
        parser.error("5DollarFootballAPI key is required")

    results = []
    failures = []
    for competition_id, name in COMPETITIONS:
        print(f"BATCH_START {name} ({competition_id})", flush=True)
        existing = completed_run(database_url, competition_id, start_at, end_at)
        if existing:
            run_id, report = existing
            results.append({"competition": name, "competition_id": competition_id,
                            "status": "SKIPPED_ALREADY_VALIDATED", "import_run_id": run_id,
                            "records_inserted": report["records_inserted"],
                            "requests_used": report["requests_used"]})
            print(json.dumps(results[-1], sort_keys=True), flush=True)
            continue
        try:
            resume = resumable_run(database_url, competition_id, start_at, end_at)
            if resume:
                resume_id, original_budget, requests_used, prior_status = resume
                print(
                    f"RESUMING import_run_id={resume_id} status={prior_status} "
                    f"requests_used={requests_used}/{original_budget}",
                    flush=True,
                )
                run_id = asyncio.run(run_competition_historical_import(
                    database_url, api_key=api_key, execute=True,
                    import_run_id=resume_id,
                    approval=FIVEDOLLAR_COMMUNITY_APPROVAL,
                    boundary_start=start_at, boundary_end=end_at,
                    request_budget=original_budget, competition_id=competition_id,
                ))
            else:
                run_id = asyncio.run(run_competition_historical_import(
                    database_url, api_key=api_key, execute=True,
                    approval=FIVEDOLLAR_COMMUNITY_APPROVAL,
                    boundary_start=start_at, boundary_end=end_at,
                    request_budget=args.request_budget, competition_id=competition_id,
                ))
            with psycopg.connect(database_url) as connection:
                report = validate_competition_import(connection, run_id, competition_id)
            results.append({"competition": name, "competition_id": competition_id,
                            "status": "COMPLETED_VALIDATED", "import_run_id": run_id,
                            "records_inserted": report["records_inserted"],
                            "requests_used": report["requests_used"]})
            print(json.dumps(results[-1], sort_keys=True), flush=True)
        except Exception as exc:  # noqa: BLE001 - isolate each competition so later imports still run
            item = {"competition": name, "competition_id": competition_id,
                    "status": "FAILED_OR_PAUSED", "error_code": type(exc).__name__,
                    "message": str(exc)[:500]}
            failures.append(item)
            results.append(item)
            print(json.dumps(item, sort_keys=True), flush=True)
            # Continue to the next competition; each importer run is independently scoped.
    summary = {"competitions_total": len(COMPETITIONS), "results": results,
               "failed_competitions": len(failures)}
    print("BATCH_SUMMARY " + json.dumps(summary, sort_keys=True), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
