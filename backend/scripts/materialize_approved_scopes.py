"""Plan or safely materialize canonical source-local entities for approved scopes.

Default mode is read-only and inventories every currently effective competition
approval. Writes require an exact provider/source/competition selector and a
separate typed confirmation. This command never calls a football-data provider.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.canonicalization import (
    CanonicalMaterializationScope,
    build_canonical_materialization_plan,
    materialize_canonical_entities,
)

EXPECTED_DATABASE = "veltrix_ai_analyst"
EXECUTE_CONFIRMATION = "APPLY_ONE_APPROVED_CANONICAL_SCOPE"


def _approved_scopes(connection: psycopg.Connection[Any]) -> list[CanonicalMaterializationScope]:
    """Return only approvals effective now; planner independently validates each scope."""
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT approval.approval_id, approval.provider, approval.source_id,
                   approval.scope_values, approval.valid_from, approval.valid_until,
                   COALESCE(latest.status, approval.status) AS effective_status
            FROM veltrix_ai_analyst.source_approvals approval
            LEFT JOIN LATERAL (
                SELECT event.status
                FROM veltrix_ai_analyst.source_approval_status_events event
                WHERE event.approval_id = approval.approval_id
                  AND event.effective_at <= statement_timestamp()
                ORDER BY event.effective_at DESC, event.id DESC
                LIMIT 1
            ) latest ON TRUE
            WHERE approval.scope_type = 'competition_id'
              AND COALESCE(latest.status, approval.status) = 'APPROVED'
              AND approval.valid_from <= statement_timestamp()
              AND (approval.valid_until IS NULL
                   OR approval.valid_until > statement_timestamp())
            ORDER BY approval.provider, approval.source_id, approval.approval_id
            """
        )
        approvals = cursor.fetchall()

    scopes: list[CanonicalMaterializationScope] = []
    for approval in approvals:
        values = approval["scope_values"]
        if isinstance(values, str):
            values = json.loads(values)
        if not isinstance(values, list):
            continue
        for competition_id in sorted({str(value) for value in values if value is not None}):
            scopes.append(
                CanonicalMaterializationScope(
                    provider=approval["provider"],
                    source_id=approval["source_id"],
                    competition_id=competition_id,
                    rights_approval_id=approval["approval_id"],
                    import_run_id=None,
                )
            )
    return scopes


def _select_scope(
    scopes: list[CanonicalMaterializationScope],
    provider: str | None,
    source_id: str | None,
    competition_id: str | None,
) -> list[CanonicalMaterializationScope]:
    selectors = (provider, source_id, competition_id)
    if any(selectors) and not all(selectors):
        raise ValueError("EXACT_SCOPE_REQUIRES_PROVIDER_SOURCE_AND_COMPETITION")
    if not any(selectors):
        return scopes
    return [
        scope for scope in scopes
        if (scope.provider, scope.source_id, scope.competition_id)
        == (provider, source_id, competition_id)
    ]


def run(
    connection: psycopg.Connection[Any],
    *,
    execute: bool = False,
    provider: str | None = None,
    source_id: str | None = None,
    competition_id: str | None = None,
) -> dict[str, Any]:
    scopes = _select_scope(
        _approved_scopes(connection), provider, source_id, competition_id
    )
    reports: list[dict[str, Any]] = []
    for scope in scopes:
        if execute:
            with connection.transaction():
                connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                connection.execute("SET LOCAL lock_timeout = '15s'")
                connection.execute("SET LOCAL statement_timeout = '180s'")
                plan = build_canonical_materialization_plan(connection, scope)
                if not plan.ready:
                    reports.append({
                        "scope": scope.__dict__,
                        "status": "BLOCKED",
                        "plan": plan.as_dict(),
                    })
                    continue
                result = materialize_canonical_entities(
                    connection, execute=True, scope=scope
                )
                reports.append({
                    "scope": scope.__dict__,
                    "status": "APPLIED",
                    "plan": plan.as_dict(),
                    "result": result,
                })
        else:
            plan = build_brazil_serie_b_materialization_plan(connection, scope)
            reports.append({
                "scope": scope.__dict__,
                "status": "READY" if plan.ready else "BLOCKED",
                "plan": plan.as_dict(),
            })

    return {
        "report_version": "1",
        "mode": "APPLY" if execute else "DRY_RUN",
        "database": EXPECTED_DATABASE,
        "provider_requests_made": 0,
        "scope_count": len(scopes),
        "ready_count": sum(item["status"] in {"READY", "APPLIED"} for item in reports),
        "blocked_count": sum(item["status"] == "BLOCKED" for item in reports),
        "scopes": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--provider")
    parser.add_argument("--source-id")
    parser.add_argument("--competition-id")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL", "")
    expected_database = os.environ.get("EXPECTED_DATABASE_NAME", "")
    if not database_url or expected_database != EXPECTED_DATABASE:
        print("CANONICAL_SCOPE_DATABASE_CONFIGURATION_INVALID", file=sys.stderr)
        return 2
    if args.execute:
        if os.environ.get("CANONICAL_MATERIALIZATION_CONFIRMATION") != EXECUTE_CONFIRMATION:
            print("CANONICAL_SCOPE_EXECUTION_CONFIRMATION_REQUIRED", file=sys.stderr)
            return 2
        if not all((args.provider, args.source_id, args.competition_id)):
            print("CANONICAL_SCOPE_EXECUTION_REQUIRES_EXACT_SCOPE", file=sys.stderr)
            return 2
    elif any((args.provider, args.source_id, args.competition_id)) and not all(
        (args.provider, args.source_id, args.competition_id)
    ):
        print("CANONICAL_SCOPE_SELECTOR_INCOMPLETE", file=sys.stderr)
        return 2

    try:
        options = None if args.execute else "-c default_transaction_read_only=on"
        with psycopg.connect(database_url, options=options, autocommit=True) as connection:
            if connection.info.dbname != EXPECTED_DATABASE:
                print("CANONICAL_SCOPE_DATABASE_TARGET_MISMATCH", file=sys.stderr)
                return 2
            if args.execute:
                report = run(
                    connection,
                    execute=True,
                    provider=args.provider,
                    source_id=args.source_id,
                    competition_id=args.competition_id,
                )
            else:
                with connection.transaction():
                    connection.execute("SET TRANSACTION READ ONLY")
                    report = run(
                        connection,
                        execute=False,
                        provider=args.provider,
                        source_id=args.source_id,
                        competition_id=args.competition_id,
                    )
    except Exception as exc:
        print(f"CANONICAL_SCOPE_MATERIALIZATION_FAILED:{type(exc).__name__}", file=sys.stderr)
        return 2

    print(json.dumps(report, sort_keys=True, indent=2, default=str))
    if report["scope_count"] == 0:
        return 3
    if report["blocked_count"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
