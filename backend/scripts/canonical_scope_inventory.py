"""Read-only inventory of canonicalization coverage across approved source scopes."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import psycopg
from psycopg.rows import dict_row

EXPECTED_DB = "veltrix_ai_analyst"
REQUIRED_MIGRATIONS = {"006_pre_match_feature_pit_gate.sql", "007_canonical_entity_layer.sql", "008_model_artifacts.sql", "008_canonical_identity_link_uniqueness.sql", "009_canonical_identity_review_cases.sql", "010_system_observed_pit.sql", "011_import_run_competition_scope.sql", "012_database_observed_timestamps.sql", "013_target_fixture_pre_match_gate.sql", "014_prediction_publication_storage.sql"}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return value


def inventory(connection: psycopg.Connection[Any]) -> dict[str, Any]:
    with connection.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT approval.approval_id, approval.provider, approval.source_id,
                   approval.scope_type, approval.scope_values, approval.data_types,
                   approval.permitted_uses, approval.status AS recorded_status,
                   approval.valid_from, approval.valid_until,
                   approval.commercial_use_allowed, approval.evidence_uri,
                   approval.evidence_sha256,
                   COALESCE(latest.status, approval.status) AS effective_status,
                   COALESCE(latest.effective_at, approval.valid_from) AS effective_status_at,
                   (approval.valid_from <= statement_timestamp() AND (approval.valid_until IS NULL OR approval.valid_until > statement_timestamp())) AS approval_in_validity_interval
            FROM veltrix_ai_analyst.source_approvals approval
            LEFT JOIN LATERAL (
                SELECT event.status, event.effective_at
                FROM veltrix_ai_analyst.source_approval_status_events event
                WHERE event.approval_id = approval.approval_id
                  AND event.effective_at <= statement_timestamp()
                ORDER BY event.effective_at DESC, event.id DESC
                LIMIT 1
            ) latest ON TRUE
            WHERE approval.scope_type = 'competition_id'
            ORDER BY approval.provider, approval.source_id, approval.approval_id
        """)
        approvals = cur.fetchall()
        cur.execute("SELECT version FROM public.schema_migrations ORDER BY version")
        applied = {row["version"] for row in cur.fetchall()}
        cur.execute("""
            SELECT to_regclass('veltrix_ai_analyst.provider_competitions') IS NOT NULL AS competitions,
                   to_regclass('veltrix_ai_analyst.provider_teams') IS NOT NULL AS teams,
                   to_regclass('veltrix_ai_analyst.provider_fixtures') IS NOT NULL AS fixtures,
                   to_regclass('veltrix_ai_analyst.source_observations') IS NOT NULL AS observations,
                   to_regclass('veltrix_ai_analyst.source_observation_sightings') IS NOT NULL AS sightings,
                   to_regclass('veltrix_ai_analyst.canonical_fixture_sources') IS NOT NULL AS fixture_links,
                   to_regclass('veltrix_ai_analyst.provider_team_identity_links') IS NOT NULL AS team_identity_links,
                   to_regclass('veltrix_ai_analyst.provider_competition_identity_links') IS NOT NULL AS competition_identity_links,
                   to_regclass('veltrix_ai_analyst.canonical_teams') IS NOT NULL AS canonical_teams,
                   to_regclass('veltrix_ai_analyst.canonical_competitions') IS NOT NULL AS canonical_competitions,
                   to_regclass('veltrix_ai_analyst.canonical_fixtures') IS NOT NULL AS canonical_fixtures,
                   to_regclass('veltrix_ai_analyst.canonical_identity_review_cases') IS NOT NULL AS identity_review_cases,
                   to_regclass('veltrix_ai_analyst.canonical_identity_review_case_events') IS NOT NULL AS identity_review_events,
                   to_regclass('veltrix_ai_analyst.canonical_identity_review_events') IS NOT NULL AS canonical_identity_review_events,
                   to_regclass('veltrix_ai_analyst.effective_provider_team_identity_links') IS NOT NULL AS effective_team_links,
                   to_regclass('veltrix_ai_analyst.effective_provider_competition_identity_links') IS NOT NULL AS effective_competition_links,
                   to_regclass('veltrix_ai_analyst.effective_source_approvals') IS NOT NULL AS effective_approvals,
                   to_regclass('veltrix_ai_analyst.canonical_team_alias_case_audit') IS NOT NULL AS team_alias_case_audit,
                   to_regclass('veltrix_ai_analyst.effective_canonical_team_aliases') IS NOT NULL AS effective_team_aliases,
                   to_regclass('veltrix_ai_analyst.canonical_team_identity_provenance_audit') IS NOT NULL AS team_provenance_audit,
                   to_regclass('veltrix_ai_analyst.canonical_competition_identity_provenance_audit') IS NOT NULL AS competition_provenance_audit,
                   to_regclass('veltrix_ai_analyst.canonical_fixture_source_provenance_audit') IS NOT NULL AS fixture_provenance_audit,
                   to_regclass('veltrix_ai_analyst.canonical_fixture_duplicate_case_audit') IS NOT NULL AS duplicate_case_audit,
                   to_regclass('veltrix_ai_analyst.effective_canonical_fixture_deduplication') IS NOT NULL AS effective_fixture_deduplication,
                   to_regclass('veltrix_ai_analyst.effective_canonical_fixture_sources') IS NOT NULL AS effective_fixture_sources,
                   to_regclass('veltrix_ai_analyst.effective_canonical_identity_review_cases') IS NOT NULL AS review_cases
        """)
        schema_objects = dict(cur.fetchone())

        scope_reports = []
        for approval in approvals:
            values = approval["scope_values"]
            if isinstance(values, str):
                values = json.loads(values)
            if approval["effective_status"] != "APPROVED" or not approval["approval_in_validity_interval"]:
                scope_reports.append({
                    "approval": _jsonable(approval),
                    "competition_scopes": [{"competition_id": str(v), "eligible": False, "reason": "APPROVAL_NOT_EFFECTIVELY_APPROVED_OR_OUTSIDE_VALIDITY"} for v in sorted(values)],
                })
                continue
            scopes = []
            for comp_id in sorted(map(str, values)):
                cur.execute("""
                    SELECT count(*) AS fixture_rows,
                           count(*) FILTER (WHERE status='FINISHED') AS finished,
                           count(*) FILTER (WHERE status='SCHEDULED') AS scheduled,
                           count(*) FILTER (WHERE status='LIVE') AS live,
                           count(*) FILTER (WHERE status='UNKNOWN') AS unknown_status,
                           count(*) FILTER (WHERE source_observation_id IS NOT NULL) AS fixture_observation_linked,
                           count(*) FILTER (WHERE provenance_ok) AS fixture_provenance_complete
                    FROM (
                        SELECT f.*, (
                            o.id IS NOT NULL AND o.provider=f.provider AND o.source_id=f.source_id
                            AND o.entity_type='fixture' AND o.data_type='fixtures_and_results'
                            AND o.provider_entity_id=f.provider_fixture_id
                            AND o.rights_approval_id=f.rights_approval_id
                            AND o.payload_sha256 IS NOT NULL
                            AND s.id IS NOT NULL AND s.payload_sha256=o.payload_sha256
                            AND s.provider_response_id=r.id AND r.http_status BETWEEN 200 AND 299
                            AND r.provider=f.provider AND r.source_id=f.source_id
                            AND r.rights_approval_id=f.rights_approval_id
                        ) AS provenance_ok
                        FROM veltrix_ai_analyst.provider_fixtures f
                        LEFT JOIN veltrix_ai_analyst.source_observations o ON o.id=f.source_observation_id
                        LEFT JOIN LATERAL (
                            SELECT sighting.* FROM veltrix_ai_analyst.source_observation_sightings sighting
                            WHERE sighting.source_observation_id=o.id AND sighting.payload_sha256=o.payload_sha256
                            ORDER BY sighting.retrieved_at, sighting.id LIMIT 1
                        ) s ON TRUE
                        LEFT JOIN veltrix_ai_analyst.provider_responses r ON r.id=s.provider_response_id
                        WHERE f.provider=%s AND f.source_id=%s AND f.provider_competition_id=%s
                    ) q
                """, (approval["provider"], approval["source_id"], comp_id))
                fixture_counts = dict(cur.fetchone())

                cur.execute("""
                    SELECT count(*) AS competition_rows,
                           count(*) FILTER (WHERE q.source_observation_id IS NOT NULL) AS observation_linked,
                           count(*) FILTER (WHERE q.provenance_ok) AS provenance_complete,
                           count(ci.id) AS canonical_linked_competitions,
                           count(ci.id) FILTER (WHERE ci.mapping_status='REVIEW_REQUIRED') AS identity_review_required,
                           count(ci.id) FILTER (WHERE ci.mapping_status='CONFLICT') AS identity_conflicts
                    FROM (
                        SELECT p.*, (
                            o.id IS NOT NULL AND o.provider=p.provider AND o.source_id=p.source_id
                            AND o.entity_type='competition' AND o.data_type='competition_catalogue'
                            AND o.provider_entity_id=p.provider_competition_id
                            AND o.rights_approval_id=p.rights_approval_id
                            AND o.payload_sha256 IS NOT NULL
                            AND s.id IS NOT NULL AND s.payload_sha256=o.payload_sha256
                            AND s.provider_response_id=r.id AND r.http_status BETWEEN 200 AND 299
                            AND r.provider=p.provider AND r.source_id=p.source_id
                            AND r.rights_approval_id=p.rights_approval_id
                        ) AS provenance_ok
                        FROM veltrix_ai_analyst.provider_competitions p
                        LEFT JOIN veltrix_ai_analyst.source_observations o ON o.id=p.source_observation_id
                        LEFT JOIN LATERAL (
                            SELECT sighting.* FROM veltrix_ai_analyst.source_observation_sightings sighting
                            WHERE sighting.source_observation_id=o.id AND sighting.payload_sha256=o.payload_sha256
                            ORDER BY sighting.retrieved_at, sighting.id LIMIT 1
                        ) s ON TRUE
                        LEFT JOIN veltrix_ai_analyst.provider_responses r ON r.id=s.provider_response_id
                        WHERE p.provider=%s AND p.source_id=%s AND p.provider_competition_id=%s
                    ) q
                    LEFT JOIN veltrix_ai_analyst.provider_competition_identity_links ci
                      ON ci.provider=q.provider AND ci.source_id=q.source_id
                     AND ci.provider_competition_id=q.provider_competition_id
                """, (approval["provider"], approval["source_id"], comp_id))
                competition_counts = dict(cur.fetchone())

                cur.execute("""
                    WITH ids AS (
                        SELECT home_team_provider_id AS team_id FROM veltrix_ai_analyst.provider_fixtures
                        WHERE provider=%s AND source_id=%s AND provider_competition_id=%s
                        UNION SELECT away_team_provider_id FROM veltrix_ai_analyst.provider_fixtures
                        WHERE provider=%s AND source_id=%s AND provider_competition_id=%s
                    )
                    SELECT count(*) AS referenced_team_ids,
                           count(t.provider_team_id) AS catalogued_teams,
                           count(*) FILTER (WHERE t.source_observation_id IS NOT NULL) AS observation_linked_teams,
                           count(*) FILTER (WHERE provenance_ok) AS provenance_complete_teams,
                           count(ti.id) AS canonical_linked_teams,
                           count(ti.id) FILTER (WHERE ti.mapping_status='REVIEW_REQUIRED') AS identity_review_required,
                           count(ti.id) FILTER (WHERE ti.mapping_status='CONFLICT') AS identity_conflicts
                    FROM ids
                    LEFT JOIN (
                        SELECT team.*, (
                            o.id IS NOT NULL AND o.provider=team.provider AND o.source_id=team.source_id
                            AND o.entity_type='team' AND o.data_type='team_catalogue'
                            AND o.provider_entity_id=team.provider_team_id
                            AND o.rights_approval_id=team.rights_approval_id
                            AND o.payload_sha256 IS NOT NULL
                            AND s.id IS NOT NULL AND s.payload_sha256=o.payload_sha256
                            AND s.provider_response_id=r.id AND r.http_status BETWEEN 200 AND 299
                            AND r.provider=team.provider AND r.source_id=team.source_id
                            AND r.rights_approval_id=team.rights_approval_id
                        ) AS provenance_ok
                        FROM veltrix_ai_analyst.provider_teams team
                        LEFT JOIN veltrix_ai_analyst.source_observations o ON o.id=team.source_observation_id
                        LEFT JOIN LATERAL (
                            SELECT sighting.* FROM veltrix_ai_analyst.source_observation_sightings sighting
                            WHERE sighting.source_observation_id=o.id AND sighting.payload_sha256=o.payload_sha256
                            ORDER BY sighting.retrieved_at, sighting.id LIMIT 1
                        ) s ON TRUE
                        LEFT JOIN veltrix_ai_analyst.provider_responses r ON r.id=s.provider_response_id
                    ) t ON t.provider=%s AND t.source_id=%s AND t.provider_team_id=ids.team_id
                    LEFT JOIN veltrix_ai_analyst.provider_team_identity_links ti
                      ON ti.provider=t.provider AND ti.source_id=t.source_id
                     AND ti.provider_team_id=t.provider_team_id
                """, (approval["provider"],approval["source_id"],comp_id,approval["provider"],approval["source_id"],comp_id,approval["provider"],approval["source_id"]))
                team_counts = dict(cur.fetchone())

                cur.execute("""
                    SELECT count(f.id) AS linked_fixture_rows,
                           count(source_link.id) AS source_links,
                           count(source_link.id) FILTER (WHERE source_link.mapping_status='REVIEW_REQUIRED') AS source_link_review_required,
                           count(source_link.id) FILTER (WHERE source_link.mapping_status='CONFLICT') AS source_link_conflicts,
                           count(*) FILTER (WHERE f.identity_status='VERIFIED') AS identity_verified,
                           count(*) FILTER (WHERE f.identity_status='IDENTITY_REVIEW_REQUIRED') AS identity_review_required,
                           count(*) FILTER (WHERE f.identity_status='CONFLICT') AS identity_conflicts,
                           count(*) FILTER (WHERE f.completeness_status='RECONCILED') AS completeness_reconciled,
                           count(*) FILTER (WHERE f.completeness_status='INCOMPLETE') AS incomplete,
                           count(*) FILTER (WHERE f.completeness_status='CONFLICT') AS completeness_conflicts
                    FROM veltrix_ai_analyst.provider_fixtures p
                    LEFT JOIN veltrix_ai_analyst.canonical_fixture_sources source_link
                      ON source_link.provider_fixture_row_id=p.id
                    LEFT JOIN veltrix_ai_analyst.canonical_fixtures f ON f.id=source_link.canonical_fixture_id
                    WHERE p.provider=%s AND p.source_id=%s AND p.provider_competition_id=%s
                """, (approval["provider"],approval["source_id"],comp_id))
                canonical_counts=dict(cur.fetchone())

                cur.execute("""
                    WITH scoped_fixture_links AS (
                        SELECT source_link.id
                        FROM veltrix_ai_analyst.canonical_fixture_sources source_link
                        JOIN veltrix_ai_analyst.provider_fixtures p
                          ON p.id=source_link.provider_fixture_row_id
                        WHERE p.provider=%s AND p.source_id=%s AND p.provider_competition_id=%s
                    ),
                    scoped_team_links AS (
                        SELECT link.id
                        FROM veltrix_ai_analyst.provider_team_identity_links link
                        WHERE link.provider=%s AND link.source_id=%s
                          AND EXISTS (
                              SELECT 1 FROM veltrix_ai_analyst.provider_fixtures p
                              WHERE p.provider=%s AND p.source_id=%s AND p.provider_competition_id=%s
                                AND (p.home_team_provider_id=link.provider_team_id
                                     OR p.away_team_provider_id=link.provider_team_id)
                          )
                    ),
                    scoped_competition_links AS (
                        SELECT id FROM veltrix_ai_analyst.provider_competition_identity_links
                        WHERE provider=%s AND source_id=%s AND provider_competition_id=%s
                    )
                    SELECT count(DISTINCT c.id) AS unresolved_cases
                    FROM veltrix_ai_analyst.canonical_identity_review_cases c
                    JOIN veltrix_ai_analyst.effective_canonical_identity_review_cases e ON e.id=c.id
                    WHERE e.effective_case_status NOT IN ('HUMAN_CONFIRMED','HUMAN_REJECTED','DEFERRED')
                      AND (
                          c.primary_fixture_source_link_id IN (SELECT id FROM scoped_fixture_links)
                          OR c.related_fixture_source_link_id IN (SELECT id FROM scoped_fixture_links)
                          OR c.primary_team_identity_link_id IN (SELECT id FROM scoped_team_links)
                          OR c.related_team_identity_link_id IN (SELECT id FROM scoped_team_links)
                          OR c.competition_identity_link_id IN (SELECT id FROM scoped_competition_links)
                      )
                """, (
                    approval["provider"], approval["source_id"], comp_id,
                    approval["provider"], approval["source_id"],
                    approval["provider"], approval["source_id"], comp_id,
                    approval["provider"], approval["source_id"], comp_id,
                ))
                unresolved=int(cur.fetchone()["unresolved_cases"])
                cur.execute("""
                    WITH scoped_fixture_links AS (
                        SELECT source_link.id
                        FROM veltrix_ai_analyst.canonical_fixture_sources source_link
                        JOIN veltrix_ai_analyst.provider_fixtures p
                          ON p.id=source_link.provider_fixture_row_id
                        WHERE p.provider=%s AND p.source_id=%s AND p.provider_competition_id=%s
                    ),
                    scoped_team_links AS (
                        SELECT link.id
                        FROM veltrix_ai_analyst.provider_team_identity_links link
                        WHERE link.provider=%s AND link.source_id=%s
                          AND EXISTS (
                              SELECT 1 FROM veltrix_ai_analyst.provider_fixtures p
                              WHERE p.provider=%s AND p.source_id=%s AND p.provider_competition_id=%s
                                AND (p.home_team_provider_id=link.provider_team_id
                                     OR p.away_team_provider_id=link.provider_team_id)
                          )
                    ),
                    scoped_competition_links AS (
                        SELECT id FROM veltrix_ai_analyst.provider_competition_identity_links
                        WHERE provider=%s AND source_id=%s AND provider_competition_id=%s
                    )
                    SELECT c.case_type, e.effective_case_status,
                           count(DISTINCT c.id) AS case_count
                    FROM veltrix_ai_analyst.canonical_identity_review_cases c
                    JOIN veltrix_ai_analyst.effective_canonical_identity_review_cases e ON e.id=c.id
                    WHERE (
                        c.primary_fixture_source_link_id IN (SELECT id FROM scoped_fixture_links)
                        OR c.related_fixture_source_link_id IN (SELECT id FROM scoped_fixture_links)
                        OR c.primary_team_identity_link_id IN (SELECT id FROM scoped_team_links)
                        OR c.related_team_identity_link_id IN (SELECT id FROM scoped_team_links)
                        OR c.competition_identity_link_id IN (SELECT id FROM scoped_competition_links)
                    )
                    GROUP BY c.case_type, e.effective_case_status
                    ORDER BY c.case_type, e.effective_case_status
                """, (
                    approval["provider"], approval["source_id"], comp_id,
                    approval["provider"], approval["source_id"],
                    approval["provider"], approval["source_id"], comp_id,
                    approval["provider"], approval["source_id"], comp_id,
                ))
                review_case_breakdown = [dict(row) for row in cur.fetchall()]
                scopes.append({
                    "competition_id": comp_id,
                    "competition_coverage": _jsonable(competition_counts),
                    "fixture_coverage": _jsonable(fixture_counts),
                    "team_coverage": _jsonable(team_counts),
                    "review_case_breakdown": _jsonable(review_case_breakdown),
                    "canonical_fixture_links": _jsonable(canonical_counts),
                    "unresolved_linked_review_cases": unresolved,
                    "inventory_only": True,
                })
            scope_reports.append({"approval": _jsonable(approval), "competition_scopes": scopes})

    missing_objects=[name for name,exists in schema_objects.items() if not exists]
    missing_migrations=sorted(REQUIRED_MIGRATIONS-applied)
    return {
        "report_version": "1",
        "read_only": True,
        "provider_requests": 0,
        "database": EXPECTED_DB,
        "schema_objects": schema_objects,
        "missing_schema_objects": missing_objects,
        "applied_migrations": sorted(applied),
        "missing_required_migrations": missing_migrations,
        "migration_readiness": not missing_migrations and not missing_objects,
        "approvals": scope_reports,
    }


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json","text","both"), default="both")
    parser.add_argument("--output", help="Optional JSON report file path")
    args=parser.parse_args()
    url=os.environ.get("DATABASE_URL","")
    expected=os.environ.get("EXPECTED_DATABASE_NAME",EXPECTED_DB)
    if not url or expected != EXPECTED_DB:
        print("CANONICAL_SCOPE_INVENTORY_DATABASE_CONFIGURATION_INVALID",file=sys.stderr)
        return 2
    try:
        with psycopg.connect(url, options="-c default_transaction_read_only=on") as connection:
            if connection.info.dbname != EXPECTED_DB:
                print("CANONICAL_SCOPE_INVENTORY_DATABASE_TARGET_MISMATCH",file=sys.stderr)
                return 2
            with connection.transaction():
                connection.execute("SET TRANSACTION READ ONLY")
                report=inventory(connection)
    except (psycopg.Error, OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
        print(f"CANONICAL_SCOPE_INVENTORY_FAILED: {type(exc).__name__}",file=sys.stderr)
        return 2
    encoded=json.dumps(report,sort_keys=True,indent=2,default=str)
    if args.output:
        with open(args.output,"w",encoding="utf-8") as stream:
            stream.write(encoded+"\n")
    if args.format in ("json","both"):
        print(encoded)
    if args.format in ("text","both"):
        print("\nCANONICAL SCOPE INVENTORY SUMMARY")
        print(f"database: {report['database']}")
        print(f"migration readiness: {'READY' if report['migration_readiness'] else 'BLOCKED'}")
        if report["missing_required_migrations"]:
            print("missing migrations: "+", ".join(report["missing_required_migrations"]))
        if report["missing_schema_objects"]:
            print("missing schema objects: "+", ".join(report["missing_schema_objects"]))
        for approval_report in report["approvals"]:
            approval=approval_report["approval"]
            print(f"approval: {approval['approval_id']} [{approval['effective_status']}]")
            for scope in approval_report["competition_scopes"]:
                if "fixture_coverage" not in scope:
                    print(f"  competition {scope['competition_id']}: BLOCKED ({scope['reason']})")
                    continue
                competitions=scope["competition_coverage"]
                fixtures=scope["fixture_coverage"]
                teams=scope["team_coverage"]
                links=scope["canonical_fixture_links"]
                print(f"  competition {scope['competition_id']}: competition_provenance={competitions['provenance_complete']}/{competitions['competition_rows']}; fixtures={fixtures['fixture_rows']} provenance={fixtures['fixture_provenance_complete']}; teams={teams['referenced_team_ids']} provenance={teams['provenance_complete_teams']}; linked={links['linked_fixture_rows']} verified={links['identity_verified']} review={links['identity_review_required']} conflicts={links['identity_conflicts']}; unresolved_cases={scope['unresolved_linked_review_cases']}")
    return 0 if report["migration_readiness"] else 3


if __name__=="__main__":
    raise SystemExit(main())
