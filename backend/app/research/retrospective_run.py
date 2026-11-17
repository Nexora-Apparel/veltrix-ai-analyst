"""Read-only runner for retrospective model research on collected provider results.

Usage:
  DATABASE_URL=... python -m app.research.retrospective_run --output artifacts/retrospective-report.json

The runner uses provider-local team IDs rather than unresolved canonical mappings.
It never writes to the production database and labels all metrics as retrospective,
not historically point-in-time certified.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.models.attack_defence import GoalResult
from app.validation.retrospective import evaluate_retrospective

DATABASE_NAME = "veltrix_ai_analyst"
PROVIDER = "5DollarFootballAPI"
SOURCE_ID = "5dollarfootballapi"


def load_completed_results(dsn: str) -> list[GoalResult]:
    """Load the existing finished corpus through a read-only transaction."""
    rows: list[dict[str, Any]]
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
        raise RuntimeError("no finished provider fixtures found for the configured source")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/retrospective-report.json"))
    parser.add_argument("--min-train", type=int, default=60)
    parser.add_argument("--test-window", type=int, default=25)
    parser.add_argument("--half-life-days", type=float, default=180.0)
    parser.add_argument("--ridge", type=float, default=0.08)
    parser.add_argument("--nested-tuning", action="store_true")
    args = parser.parse_args()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is required; no database credentials are embedded")
    results = load_completed_results(dsn)
    report = evaluate_retrospective(
        results,
        min_train_fixtures=args.min_train,
        test_window_fixtures=args.test_window,
        half_life_days=args.half_life_days,
        ridge=args.ridge,
        rho=0.0,
        nested_tuning=args.nested_tuning,
    )
    payload = {
        "created_at": datetime.now().astimezone().isoformat(),
        "provider": PROVIDER,
        "source_id": SOURCE_ID,
        "dataset_basis": "FINISHED_PROVIDER_ROWS_PROVIDER_LOCAL_TEAM_IDS",
        "identity_policy": "UNRESOLVED_CANONICAL_IDENTITIES_NOT_MERGED",
        "evaluation_type": report.evaluation_type,
        "historical_publication_availability_timestamps": "NOT_VERIFIED",
        "model": "RECENCY_WEIGHTED_REGULARIZED_ATTACK_DEFENCE_POISSON",
        "parameters": {
            "min_train_fixtures": args.min_train,
            "test_window_fixtures": args.test_window,
            "half_life_days": args.half_life_days,
            "ridge": args.ridge,
            "dixon_coles_rho": 0.0,
        },
        "metrics": {
            "finished_fixtures_loaded": len(results),
            "initial_training_fixtures": report.training_fixtures,
            "evaluated_fixtures": report.evaluated_fixtures,
            "fold_count": report.fold_count,
            "brier_1x2": report.brier_1x2,
            "log_loss_1x2": report.log_loss_1x2,
            "mean_scoreline_log_loss": report.mean_scoreline_log_loss,
            "league_baseline_brier_1x2": report.baseline_brier_1x2,
            "league_baseline_log_loss_1x2": report.baseline_log_loss_1x2,
            "nested_tuning": report.nested_tuning,
            "classwise_ece": report.classwise_ece,
            "top_label_ece": report.top_label_ece,
            "calibrated_brier_1x2": report.calibrated_brier_1x2,
            "calibrated_log_loss_1x2": report.calibrated_log_loss_1x2,
            "calibrated_classwise_ece": report.calibrated_classwise_ece,
            "calibrated_top_label_ece": report.calibrated_top_label_ece,
            "paired_fold_block_bootstrap": {
                "resamples": report.paired_bootstrap.resamples,
                "seed": report.paired_bootstrap.seed,
                "difference_convention": "MODEL_MINUS_LEAGUE_BASELINE; NEGATIVE_FAVOURS_MODEL",
                "brier_difference": {
                    "mean": report.paired_bootstrap.brier_difference.mean_difference,
                    "lower_95": report.paired_bootstrap.brier_difference.lower_95,
                    "upper_95": report.paired_bootstrap.brier_difference.upper_95,
                },
                "log_loss_difference": {
                    "mean": report.paired_bootstrap.log_loss_difference.mean_difference,
                    "lower_95": report.paired_bootstrap.log_loss_difference.lower_95,
                    "upper_95": report.paired_bootstrap.log_loss_difference.upper_95,
                },
                "interpretation": "EXPLORATORY_CHRONOLOGICAL_FOLD_BLOCK_BOOTSTRAP_FEW_FOLDS",
            },
            "fold_metrics": [
                {
                    "fold_index": row.fold_index,
                    "fixture_count": row.fixture_count,
                    "test_start_at": row.test_start_at.isoformat(),
                    "test_end_at": row.test_end_at.isoformat(),
                    "brier_1x2": row.brier_1x2,
                    "log_loss_1x2": row.log_loss_1x2,
                    "baseline_brier_1x2": row.baseline_brier_1x2,
                    "baseline_log_loss_1x2": row.baseline_log_loss_1x2,
                    "mean_scoreline_log_loss": row.mean_scoreline_log_loss,
                    "half_life_days": row.half_life_days,
                    "ridge": row.ridge,
                    "rho": row.rho,
                    "classwise_ece": row.classwise_ece,
                    "top_label_ece": row.top_label_ece,
                    "calibrated_brier_1x2": row.calibrated_brier_1x2,
                    "calibrated_log_loss_1x2": row.calibrated_log_loss_1x2,
                    "calibrated_classwise_ece": row.calibrated_classwise_ece,
                    "calibrated_top_label_ece": row.calibrated_top_label_ece,
                    "temperature": row.temperature,
                    "calibration_samples": row.calibration_samples,
                }
                for row in report.fold_metrics
            ],
            "selected_parameters_by_fold": [
                {
                    "half_life_days": values[0],
                    "ridge": values[1],
                    "rho": values[2],
                }
                for values in report.selected_parameters
            ],
        },
        "predictions": [
            {
                "fixture_id": row.fixture_id,
                "kickoff_at": row.kickoff_at.isoformat(),
                "actual_score": [row.actual_home_goals, row.actual_away_goals],
                "expected_goals": [row.home_lambda, row.away_lambda],
                "calibrated_probabilities_1x2": {
                    "home": row.calibrated_home_win,
                    "draw": row.calibrated_draw,
                    "away": row.calibrated_away_win,
                },
                "temperature": row.temperature,
                "calibration_samples": row.calibration_samples,
                "probabilities_1x2": {
                    "home": row.home_win,
                    "draw": row.draw,
                    "away": row.away_win,
                },
                "actual_scoreline_probability": row.scoreline_probability,
            }
            for row in report.predictions
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["metrics"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
