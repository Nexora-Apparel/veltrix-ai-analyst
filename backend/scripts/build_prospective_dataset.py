"""Read-only builder for leakage-safe prospective training datasets."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import psycopg

from app.validation.prospective_dataset import (
    FixtureIdentity,
    FixtureObservation,
    build_expanding_window_folds,
    build_prospective_dataset,
)


def _jsonable_row(row) -> dict:
    return {
        "fixture_id": row.fixture_id,
        "provider_fixture_id": row.fixture_id.split(":", 1)[1],
        "provider_competition_id": row.competition_id,
        "canonical_fixture_id": row.canonical_fixture_id,
        "canonical_competition_id": row.canonical_competition_id,
        "provider": row.provider,
        "source_id": row.source_id,
        "competition_id": row.competition_id,
        "kickoff_at": row.kickoff_at.isoformat(),
        "prediction_cutoff_at": row.prediction_cutoff_at.isoformat(),
        "home_team_id": row.home_team_id,
        "away_team_id": row.away_team_id,
        "features": row.features,
        "feature_lineage": list(row.feature_lineage),
        "label": row.label,
        "label_observed_at": (
            row.label_observed_at.isoformat() if row.label_observed_at else None
        ),
        "label_observation_id": row.label_observation_id,
        "label_lineage": row.label_lineage,
    }


def build_report(
    database_url: str,
    *,
    expected_database: str,
    minimum_training_fixtures: int,
    validation_block_fixtures: int,
) -> dict:
    if urlsplit(database_url).path.lstrip("/").split("?", 1)[0] != expected_database:
        raise RuntimeError("DATABASE_URL_PATH_MISMATCH")
    with psycopg.connect(database_url, autocommit=True) as connection:
        if connection.info.dbname != expected_database:
            raise RuntimeError("DATABASE_NAME_MISMATCH")
        connection.execute("SET default_transaction_read_only = on")
        fixture_rows = connection.execute(
            """
            SELECT pf.provider, pf.source_id, pf.provider_fixture_id,
                   pf.provider_competition_id, ht.canonical_team_id::text,
                   at.canonical_team_id::text, pf.kickoff_at,
                   cf.id::text AS canonical_fixture_id,
                   cc.canonical_competition_id::text AS canonical_competition_id,
                   pf.home_team_provider_id, pf.away_team_provider_id
            FROM veltrix_ai_analyst.provider_fixtures pf
            JOIN veltrix_ai_analyst.effective_canonical_fixture_sources link
              ON link.provider_fixture_row_id = pf.id
             AND link.provider = pf.provider
             AND link.source_id = pf.source_id
             AND link.effective_mapping_status = 'SOURCE_FIXTURE_LINK_REVIEWED'
            JOIN veltrix_ai_analyst.canonical_fixture_source_provenance_audit provenance
              ON provenance.fixture_source_link_id = link.id
             AND provenance.source_fixture_provenance_status = 'PROVENANCE_VERIFIED'
             AND provenance.effective_review_status = 'SOURCE_FIXTURE_LINK_REVIEWED'
            JOIN veltrix_ai_analyst.canonical_fixtures cf
              ON cf.id = link.canonical_fixture_id
             AND cf.identity_status = 'VERIFIED'
            JOIN veltrix_ai_analyst.effective_provider_team_identity_links ht
              ON ht.provider = pf.provider AND ht.source_id = pf.source_id
             AND ht.provider_team_id = pf.home_team_provider_id
             AND ht.effective_mapping_status IN (
                 'SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED'
             )
            JOIN veltrix_ai_analyst.effective_provider_team_identity_links at
              ON at.provider = pf.provider AND at.source_id = pf.source_id
             AND at.provider_team_id = pf.away_team_provider_id
             AND at.effective_mapping_status IN (
                 'SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED'
             )
            JOIN veltrix_ai_analyst.effective_provider_competition_identity_links cc
              ON cc.provider = pf.provider AND cc.source_id = pf.source_id
             AND cc.provider_competition_id = pf.provider_competition_id
             AND cc.effective_mapping_status IN (
                 'SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED'
             )
             AND cc.canonical_competition_id = cf.canonical_competition_id
            WHERE pf.provider = '5DollarFootballAPI'
              AND pf.source_id = '5dollarfootballapi'
            ORDER BY pf.kickoff_at, pf.provider_fixture_id
            """
        ).fetchall()
        invalid_system_observed = connection.execute(
            """
            SELECT COUNT(*)
            FROM veltrix_ai_analyst.source_observations o
            JOIN veltrix_ai_analyst.source_observation_sightings s
              ON s.source_observation_id = o.id
            LEFT JOIN veltrix_ai_analyst.provider_responses r
              ON r.id = s.provider_response_id
            LEFT JOIN veltrix_ai_analyst.source_approvals a
              ON a.approval_id = o.rights_approval_id
            WHERE o.provider = '5DollarFootballAPI'
              AND o.source_id = '5dollarfootballapi'
              AND o.data_type = 'fixtures_and_results'
              AND o.entity_type = 'fixture'
              AND s.availability_basis = 'SYSTEM_OBSERVED_AT'
              AND s.point_in_time_certifiable IS TRUE
              AND (
                s.system_observed_at IS NULL
                OR s.available_at IS DISTINCT FROM s.system_observed_at
                OR s.system_observed_at < s.retrieved_at
                OR s.source_published_at IS NOT NULL
                OR s.provider_response_id IS NULL
                OR s.payload_sha256 IS NULL
                OR s.payload_sha256 IS DISTINCT FROM o.payload_sha256
                OR length(s.payload_sha256) <> 64
                OR o.payload->>'competition_id' IS NULL
                OR o.payload->>'home_team_id' IS NULL
                OR o.payload->>'away_team_id' IS NULL
                OR o.payload->>'kickoff_at' IS NULL
                OR o.payload #>> '{provenance,provider_record_id}'
                    IS DISTINCT FROM o.provider_entity_id
                OR r.id IS NULL
                OR r.provider IS DISTINCT FROM o.provider
                OR r.source_id IS DISTINCT FROM o.source_id
                OR r.http_status NOT BETWEEN 200 AND 299
                OR r.fetched_at IS DISTINCT FROM s.retrieved_at
                OR r.system_observed_at IS DISTINCT FROM s.system_observed_at
                OR r.response_sha256 IS NULL
                OR length(r.response_sha256) <> 64
                OR a.approval_id IS NULL
                OR a.status <> 'APPROVED'
                OR a.valid_from > s.system_observed_at
                OR (a.valid_until IS NOT NULL AND a.valid_until <= s.system_observed_at)
                OR NOT (
                    a.permitted_uses @> '["FEATURE_ENGINEERING", "MODEL_TRAINING", "MODEL_VALIDATION"]'::jsonb
                )
              )
            """
        ).fetchone()[0]
        if invalid_system_observed:
            raise RuntimeError(
                f"PROSPECTIVE_SOURCE_PROVENANCE_AUDIT_FAILED:{invalid_system_observed}"
            )
        observation_rows = connection.execute(
            """
            SELECT o.id, s.id, s.provider_response_id,
                   o.provider, o.source_id, o.provider_entity_id,
                   o.payload->>'competition_id' AS competition_id,
                   s.retrieved_at, s.system_observed_at,
                   s.availability_basis, s.point_in_time_certifiable,
                   s.payload_sha256, r.response_sha256, o.payload,
                   o.rights_approval_id, a.status, a.valid_from, a.valid_until,
                   a.permitted_uses, approval_events.status_events
            FROM veltrix_ai_analyst.source_observations o
            JOIN veltrix_ai_analyst.source_observation_sightings s
              ON s.source_observation_id = o.id
            JOIN veltrix_ai_analyst.provider_responses r
              ON r.id = s.provider_response_id
             AND r.provider = o.provider
             AND r.source_id = o.source_id
             AND r.http_status BETWEEN 200 AND 299
             AND r.fetched_at = s.retrieved_at
             AND r.system_observed_at = s.system_observed_at
            JOIN veltrix_ai_analyst.source_approvals a
              ON a.approval_id = o.rights_approval_id
            LEFT JOIN LATERAL (
                SELECT COALESCE(
                    jsonb_agg(
                        jsonb_build_object(
                            'id', e.id,
                            'status', e.status,
                            'effective_at', e.effective_at
                        ) ORDER BY e.effective_at, e.id
                    ),
                    '[]'::jsonb
                ) AS status_events
                FROM veltrix_ai_analyst.source_approval_status_events e
                WHERE e.approval_id = a.approval_id
            ) approval_events ON TRUE
            WHERE o.provider = '5DollarFootballAPI'
              AND o.source_id = '5dollarfootballapi'
              AND o.data_type = 'fixtures_and_results'
              AND o.entity_type = 'fixture'
              AND s.provider_response_id IS NOT NULL
              AND s.system_observed_at IS NOT NULL
              AND s.available_at = s.system_observed_at
              AND s.system_observed_at >= s.retrieved_at
              AND s.availability_basis = 'SYSTEM_OBSERVED_AT'
              AND s.point_in_time_certifiable IS TRUE
              AND s.payload_sha256 = o.payload_sha256
              AND o.payload->>'competition_id' IS NOT NULL
            ORDER BY s.system_observed_at, o.id, s.id
            """
        ).fetchall()

    fixtures = [
        FixtureIdentity(
            fixture_id=f"{row[3]}:{row[2]}",
            provider=str(row[0]),
            source_id=str(row[1]),
            competition_id=str(row[3]),
            home_team_id=str(row[4]),
            away_team_id=str(row[5]),
            kickoff_at=row[6],
            canonical_competition_id=str(row[8]),
            canonical_fixture_id=str(row[7]),
            provider_home_team_id=str(row[9]),
            provider_away_team_id=str(row[10]),
        )
        for row in fixture_rows
    ]
    observations = [
        FixtureObservation(
            observation_id=int(row[0]),
            sighting_id=int(row[1]),
            provider_response_id=int(row[2]),
            provider=str(row[3]),
            source_id=str(row[4]),
            fixture_id=f"{row[6]}:{row[5]}",
            retrieved_at=row[7],
            observed_at=row[8],
            availability_basis=str(row[9]),
            point_in_time_certifiable=bool(row[10]),
            payload_sha256=str(row[11]).strip(),
            raw_response_sha256=str(row[12]).strip(),
            payload=dict(row[13]),
            rights_approval_id=str(row[14]) if row[14] is not None else None,
            rights_status=str(row[15]) if row[15] is not None else None,
            rights_valid_from=row[16],
            rights_valid_until=row[17],
            rights_permitted_uses=tuple(row[18] or ()),
            rights_status_events=tuple(row[19] or ()),
        )
        for row in observation_rows
    ]
    rows = build_prospective_dataset(fixtures, observations)
    folds = build_expanding_window_folds(
        rows,
        minimum_training_fixtures=minimum_training_fixtures,
        validation_block_fixtures=validation_block_fixtures,
    )
    serialized_rows = [_jsonable_row(row) for row in rows]
    serialized_folds = [
        {
            "fold_number": fold.fold_number,
            "train_fixture_ids": list(fold.train_fixture_ids),
            "validation_fixture_ids": list(fold.validation_fixture_ids),
            "train_cutoff_at": fold.train_cutoff_at.isoformat(),
            "validation_start_at": fold.validation_start_at.isoformat(),
            "validation_end_at": fold.validation_end_at.isoformat(),
        }
        for fold in folds
    ]
    canonical = json.dumps(
        {"rows": serialized_rows, "folds": serialized_folds},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return {
        "report_type": "VELTRIX_PROSPECTIVE_EXPANDING_DATASET",
        "status": "READY_FOR_RESEARCH" if rows else "NO_PROSPECTIVE_DATA_YET",
        "created_at": datetime.now(UTC).isoformat(),
        "provider": "5DollarFootballAPI",
        "fixture_identity_rows": len(fixtures),
        "eligible_prospective_rows": len(rows),
        "settled_label_rows": sum(row.label is not None for row in rows),
        "settled_distinct_kickoff_dates": len({
            row.kickoff_at.date() for row in rows if row.label is not None
        }),
        "unsettled_rows": sum(row.label is None for row in rows),
        "distinct_competitions": len({row.competition_id for row in rows}),
        "distinct_kickoff_dates": len({row.kickoff_at.date() for row in rows}),
        "feature_lineage_records": sum(len(row.feature_lineage) for row in rows),
        "feature_coverage": {
            key: sum(1 for row in rows if key in row.features)
            for key in sorted({key for row in rows for key in row.features})
        },
        "invalid_system_observed_sightings": invalid_system_observed,
        "expanding_folds": serialized_folds,
        "dataset_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "rows": serialized_rows,
        "release_eligible": False,
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--minimum-training-fixtures", type=int, default=30)
    parser.add_argument("--validation-block-fixtures", type=int, default=25)
    args = parser.parse_args()
    database_url = (
        os.getenv("VELTRIX_AI_ANALYST_DATABASE_URL")
        or os.getenv("DATABASE_URL", "")
    ).strip()
    expected_database = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not database_url or expected_database != "veltrix_ai_analyst":
        parser.error("dedicated veltrix_ai_analyst database configuration is required")
    if args.minimum_training_fixtures < 1 or args.validation_block_fixtures < 1:
        parser.error("fold sizes must be positive")
    report = build_report(
        database_url,
        expected_database=expected_database,
        minimum_training_fixtures=args.minimum_training_fixtures,
        validation_block_fixtures=args.validation_block_fixtures,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "eligible_prospective_rows": report["eligible_prospective_rows"],
                "settled_label_rows": report["settled_label_rows"],
                "expanding_folds": len(report["expanding_folds"]),
                "dataset_sha256": report["dataset_sha256"],
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
