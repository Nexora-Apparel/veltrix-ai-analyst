"""Fit and privately persist a versioned research model from the collected corpus.

Post-merge matched v1/v2 evaluation run with fold-contained calibration utility.

Matched v1/v2 comparison and fold-contained calibration research are separate.

Retrospective report execution trigger after bootstrap diagnostics merge.

The loader is read-only. Only the final immutable model artifact is written.
This runner makes no provider requests and never changes source fixtures or identity
mappings. The artifact is retrospective and is not PIT-certified.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.models.attack_defence import GoalResult, fit_attack_defence
from app.models.elo import EloConfig, EloSystem, HistoricalResult
from app.validation.tuning import tune_attack_defence

DATABASE_NAME = "veltrix_ai_analyst"
PROVIDER = "5DollarFootballAPI"
SOURCE_ID = "5dollarfootballapi"
RIGHTS_DECLARATION_ID = "PROJECT_OWNER_PERSONAL_USE_AUTHORIZATION_2026-11-17"
MODEL_FAMILY = "RECENCY_WEIGHTED_ATTACK_DEFENCE_POISSON"
MODEL_VERSION = "attack-defence-poisson-v2-nested-tuned"


def load_completed_results(dsn: str) -> list[GoalResult]:
    """Read the finished provider corpus without changing production records."""
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        database = connection.execute("SELECT current_database() AS name").fetchone()["name"]
        if database != DATABASE_NAME:
            raise RuntimeError(f"refusing database {database!r}; expected {DATABASE_NAME!r}")
        rows = connection.execute(
            """
            SELECT
                id::text AS fixture_id,
                kickoff_at,
                home_team_provider_id AS home_team,
                away_team_provider_id AS away_team,
                home_goals,
                away_goals
            FROM veltrix_ai_analyst.provider_fixtures
            WHERE provider = %s
              AND source_id = %s
              AND status = 'FINISHED'
              AND home_goals IS NOT NULL
              AND away_goals IS NOT NULL
            ORDER BY kickoff_at, id
            """,
            (PROVIDER, SOURCE_ID),
        ).fetchall()
    results = [
        GoalResult(
            fixture_id=row["fixture_id"],
            kickoff_at=row["kickoff_at"],
            home_team=row["home_team"],
            away_team=row["away_team"],
            home_goals=row["home_goals"],
            away_goals=row["away_goals"],
        )
        for row in rows
    ]
    if not results:
        raise RuntimeError("no completed provider fixtures found")
    return results


def dataset_fingerprint(results: list[GoalResult]) -> str:
    """Fingerprint only stable source-row values used by this model fit."""
    canonical_rows = [
        {
            "fixture_id": row.fixture_id,
            "kickoff_at": row.kickoff_at.isoformat(),
            "home_team": row.home_team,
            "away_team": row.away_team,
            "home_goals": row.home_goals,
            "away_goals": row.away_goals,
        }
        for row in sorted(results, key=lambda item: (item.kickoff_at, item.fixture_id))
    ]
    payload = json.dumps(canonical_rows, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_artifact(results: list[GoalResult]) -> tuple[str, str, dict[str, Any]]:
    """Fit attack/defence and a separately retained Elo comparator."""
    cutoff = max(row.kickoff_at for row in results)
    fingerprint = dataset_fingerprint(results)
    teams = sorted({row.home_team for row in results} | {row.away_team for row in results})

    tuning = tune_attack_defence(results)
    model = fit_attack_defence(
        results,
        as_of=cutoff,
        half_life_days=tuning.half_life_days,
        ridge=tuning.ridge,
        max_iterations=3000,
    )
    elo_history = [
        HistoricalResult(
            fixture_id=row.fixture_id,
            kickoff_at=row.kickoff_at,
            home_team_id=row.home_team,
            away_team_id=row.away_team,
            home_goals=row.home_goals,
            away_goals=row.away_goals,
        )
        for row in results
    ]
    elo = EloSystem.fit_chronologically(elo_history, EloConfig())

    artifact: dict[str, Any] = {
        "artifact_schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "provider": PROVIDER,
        "source_id": SOURCE_ID,
        "dataset_fingerprint_sha256": fingerprint,
        "training_fixtures": len(results),
        "distinct_provider_team_ids": len(teams),
        "provider_team_ids": teams,
        "training_cutoff_at": cutoff.isoformat(),
        "training_basis": "FINISHED_PROVIDER_ROWS_PROVIDER_LOCAL_TEAM_IDS",
        "identity_policy": "NO_CANONICAL_ALIAS_MERGES; PROVIDER_IDS_RETAINED",
        "temporal_certification": "RETROSPECTIVE_EVENT_TIME_NOT_PIT_CERTIFIED",
        "rights_declaration_id": RIGHTS_DECLARATION_ID,
        "primary_model": {
            "family": MODEL_FAMILY,
            "version": MODEL_VERSION,
            "half_life_days": model.half_life_days,
            "ridge": model.ridge,
            "intercept": model.intercept,
            "home_advantage_log_rate": model.home_advantage,
            "attack": model.attack,
            "defence": model.defence,
            "training_fixtures": model.training_fixtures,
            "inner_tuning": {
                "half_life_days": tuning.half_life_days,
                "ridge": tuning.ridge,
                "rho": tuning.rho,
                "inner_folds": tuning.inner_folds,
                "inner_predictions": tuning.inner_predictions,
                "inner_log_loss_1x2": tuning.inner_log_loss_1x2,
                "inner_brier_1x2": tuning.inner_brier_1x2,
                "inner_scoreline_log_loss": tuning.inner_scoreline_log_loss,
            },
        },
        "elo_comparator": {
            "status": "RETAINED_FOR_RESEARCH_NOT_SELECTED_FOR_ENSEMBLE",
            "initial_rating": 1500.0,
            "k_factor": 20.0,
            "home_advantage": 55.0,
            "rating_scale": 400.0,
            "ratings": {
                team: {
                    "rating": elo.rating(team).rating,
                    "matches_played": elo.rating(team).matches_played,
                }
                for team in teams
            },
        },
        "dixon_coles": {
            "rho": tuning.rho,
            "status": (
                "SELECTED_BY_INNER_CHRONOLOGICAL_SCORELINE_LIKELIHOOD"
                if tuning.inner_folds
                else "INSUFFICIENT_INNER_FOLDS; DEFAULT_RHO_ZERO"
            ),
        },
        "deployment_status": "RESEARCH_ARTIFACT_ONLY",
    }
    artifact_id = f"v2-{fingerprint[:32]}"
    return artifact_id, fingerprint, artifact


def persist_artifact(dsn: str, artifact_id: str, fingerprint: str, artifact: dict[str, Any]) -> None:
    """Insert immutable model artifact; fail if the same ID has different content."""
    with psycopg.connect(dsn) as connection:
        if connection.info.dbname != DATABASE_NAME:
            raise RuntimeError("DATABASE_TARGET_NAME_MISMATCH")
        with connection.transaction():
            connection.execute(
                """
                INSERT INTO veltrix_ai_analyst.model_artifacts (
                    model_artifact_id, model_family, model_version,
                    training_data_fingerprint, training_fixture_count,
                    distinct_team_count, training_cutoff_at,
                    point_in_time_certified, owner_rights_declaration_id, artifact
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s)
                ON CONFLICT (model_artifact_id) DO NOTHING
                """,
                (
                    artifact_id,
                    MODEL_FAMILY,
                    MODEL_VERSION,
                    fingerprint,
                    artifact["training_fixtures"],
                    artifact["distinct_provider_team_ids"],
                    artifact["training_cutoff_at"],
                    RIGHTS_DECLARATION_ID,
                    Jsonb(artifact),
                ),
            )
            stored = connection.execute(
                """
                SELECT artifact, training_data_fingerprint
                FROM veltrix_ai_analyst.model_artifacts
                WHERE model_artifact_id = %s
                """,
                (artifact_id,),
            ).fetchone()
            if stored is None or stored[1].strip() != fingerprint:
                raise RuntimeError("MODEL_ARTIFACT_IMMUTABILITY_CHECK_FAILED")
            stored_payload = dict(stored[0])
            candidate_payload = dict(artifact)
            # created_at is metadata; the model payload must remain byte-for-byte equivalent.
            stored_payload.pop("created_at", None)
            candidate_payload.pop("created_at", None)
            if stored_payload != candidate_payload:
                raise RuntimeError("MODEL_ARTIFACT_IMMUTABILITY_CHECK_FAILED")


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL_REQUIRED")
    expected = os.environ.get("EXPECTED_DATABASE_NAME", DATABASE_NAME)
    if expected != DATABASE_NAME:
        raise RuntimeError("EXPECTED_DATABASE_NAME_MISMATCH")
    results = load_completed_results(dsn)
    artifact_id, fingerprint, artifact = build_artifact(results)
    persist_artifact(dsn, artifact_id, fingerprint, artifact)
    print(json.dumps({
        "status": "MODEL_ARTIFACT_PERSISTED",
        "model_artifact_id": artifact_id,
        "dataset_fingerprint_sha256": fingerprint,
        "training_fixtures": len(results),
        "distinct_provider_team_ids": artifact["distinct_provider_team_ids"],
        "training_cutoff_at": artifact["training_cutoff_at"],
        "primary_model": MODEL_FAMILY,
        "elo_status": artifact["elo_comparator"]["status"],
        "point_in_time_certified": False,
        "deployment_status": "RESEARCH_ARTIFACT_ONLY",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
