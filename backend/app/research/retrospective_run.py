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
    parser.add_argument(
        "--fixed",
        action="store_true",
        help="disable nested fold-contained tuning and use the supplied fixed parameters",
    )
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
        tune=not args.fixed,
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
            "dixon_coles_rho": "INNER_PREQUENTIAL_SELECTION" if not args.fixed else 0.0,
            "tuning": "NESTED_CHRONOLOGICAL" if not args.fixed else "FIXED_PARAMETERS",
        },
        "fold_parameters": [
            {
                "half_life_days": half_life,
                "ridge": fold_ridge,
                "dixon_coles_rho": rho,
            }
            for half_life, fold_ridge, rho in report.selected_parameters
        ],
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
        },
        "predictions": [
            {
                "fixture_id": row.fixture_id,
                "kickoff_at": row.kickoff_at.isoformat(),
                "actual_score": [row.actual_home_goals, row.actual_away_goals],
                "expected_goals": [row.home_lambda, row.away_lambda],
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
