"""Run retrospective-only chronological development evaluation on approved 5Dollar history.

This command never writes predictions or promotes a model. It uses provider-local IDs
without alias reconciliation, excludes non-finished fixtures, and labels every output
RETROSPECTIVE_NOT_PIT_CERTIFIED because these records were first observed after kickoff.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.models.hierarchical_poisson import HierarchicalGoalResult, fit_hierarchical_poisson
from app.models.scoreline import build_scoreline_distribution
from app.validation.dixon_coles import estimate_rho_from_development_folds
from app.validation.hierarchical_tuning import (
    ChronologicalFold,
    select_hierarchical_hyperparameters,
)
from app.validation.paired_baselines import ProbabilityForecast, compare_paired_baselines

COMPETITIONS = {
    "3118717965": "Brazil Serie A",
    "4160026622": "England Premier League",
    "3614399544": "France Ligue 1",
    "686337048": "Germany Bundesliga I",
    "3405541143": "Italy Serie A",
    "4212821298": "Spain La Liga",
}


def load_rows(connection) -> tuple[list[HierarchicalGoalResult], dict]:
    rows = connection.execute(
        """
        SELECT pf.id, pf.provider_fixture_id, pf.provider_competition_id,
               pf.home_team_provider_id, pf.away_team_provider_id,
               pf.kickoff_at, pf.status, pf.home_goals, pf.away_goals,
               pf.first_seen_at, pf.last_seen_at,
               so.availability_basis, so.point_in_time_certifiable,
               so.retrieved_at, so.source_published_at, so.available_at,
               so.provider_response_id
        FROM veltrix_ai_analyst.provider_fixtures pf
        JOIN veltrix_ai_analyst.source_observations so
          ON so.id = pf.source_observation_id
        WHERE pf.provider = '5DollarFootballAPI'
          AND pf.source_id = '5dollarfootballapi'
          AND pf.provider_competition_id = ANY(%s)
        ORDER BY pf.kickoff_at, pf.id
        """,
        (list(COMPETITIONS),),
    ).fetchall()

    issues: list[str] = []
    ids = [str(row["provider_fixture_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        issues.append("DUPLICATE_PROVIDER_FIXTURE_ID")
    if len(rows) == 0:
        raise SystemExit("NO_APPROVED_COMPETITION_ROWS")

    finished = [row for row in rows if row["status"] == "FINISHED"]
    malformed = [
        row for row in finished
        if row["home_goals"] is None or row["away_goals"] is None
        or row["home_goals"] < 0 or row["away_goals"] < 0
    ]
    if malformed:
        raise SystemExit(f"FINISHED_SCORE_INTEGRITY_FAILURE:{len(malformed)}")

    # Team identifiers remain provider-local. No name normalization or alias merging.
    results = [
        HierarchicalGoalResult(
            fixture_id=f"5dollar:{row['provider_fixture_id']}",
            kickoff_at=row["kickoff_at"],
            competition_id=str(row["provider_competition_id"]),
            home_team_id=str(row["home_team_provider_id"]),
            away_team_id=str(row["away_team_provider_id"]),
            home_goals=int(row["home_goals"]),
            away_goals=int(row["away_goals"]),
        )
        for row in finished
    ]

    pit_rows = sum(bool(row["point_in_time_certifiable"]) for row in rows)
    post_kickoff_capture = sum(row["first_seen_at"] >= row["kickoff_at"] for row in rows)
    report = {
        "dataset_status": "RETROSPECTIVE_NOT_PIT_CERTIFIED",
        "provider": "5DollarFootballAPI",
        "competitions": COMPETITIONS,
        "provider_rows": len(rows),
        "finished_rows": len(finished),
        "non_finished_rows_excluded": len(rows) - len(finished),
        "finished_missing_score": len(malformed),
        "unique_provider_fixture_ids": len(set(ids)),
        "pit_certifiable_rows": pit_rows,
        "first_seen_at_or_after_kickoff": post_kickoff_capture,
        "all_source_timestamps_preserved": True,
        "team_identity_policy": "PROVIDER_LOCAL_IDS_ONLY_NO_ALIAS_MERGING",
        "identity_review_cases_mutated": 0,
        "database_mutations": 0,
    }
    if issues:
        raise SystemExit(",".join(issues))
    return results, report


def outcome_for(row: HierarchicalGoalResult, market: str) -> str:
    if market == "1X2":
        return "HOME" if row.home_goals > row.away_goals else "AWAY" if row.home_goals < row.away_goals else "DRAW"
    if market == "BTTS":
        return "YES" if row.home_goals > 0 and row.away_goals > 0 else "NO"
    total = row.home_goals + row.away_goals
    return "OVER" if total >= 3 else "UNDER"


def evaluate_paired(results, folds, candidate, rho):
    forecasts: dict[str, list[ProbabilityForecast]] = {
        "1X2": [], "BTTS": [], "TOTALS_2_5": []
    }
    seen: set[str] = set()
    for fold in folds:
        train = [r for r in results if r.kickoff_at <= fold.train_cutoff]
        validation = [
            r for r in results
            if fold.train_cutoff < r.kickoff_at <= fold.validation_end
        ]
        if not train or not validation:
            continue
        fitted = fit_hierarchical_poisson(
            train, as_of=fold.train_cutoff,
            half_life_days=candidate.half_life_days,
            team_ridge=candidate.team_ridge,
            competition_ridge=candidate.competition_ridge,
        )
        # Baseline rates use training outcomes only; no held-out labels enter rates.
        home_rate = sum(r.home_goals for r in train) / len(train)
        away_rate = sum(r.away_goals for r in train) / len(train)
        for row in validation:
            if row.fixture_id in seen:
                raise SystemExit("OVERLAPPING_VALIDATION_FIXTURE")
            seen.add(row.fixture_id)
            rates = fitted.predict(row.home_team_id, row.away_team_id, row.competition_id)
            model_dist = build_scoreline_distribution(rates.home_lambda, rates.away_lambda, rho=rho)
            base_dist = build_scoreline_distribution(home_rate, away_rate, rho=0.0)
            model_markets = model_dist.market_probabilities()
            base_markets = base_dist.market_probabilities()
            for market, key in (("1X2", "1X2"), ("BTTS", "BTTS"), ("TOTALS_2_5", "TOTALS_2_5")):
                observed = outcome_for(row, market)
                for model_name, values in (
                    ("HIERARCHICAL_DIXON_COLES", model_markets[key]),
                    ("GLOBAL_INDEPENDENT_POISSON", base_markets[key]),
                ):
                    forecasts[market].append(ProbabilityForecast(
                        fixture_id=row.fixture_id,
                        model_name=model_name,
                        probabilities=values,
                        outcome=observed,
                    ))
    reports = {}
    for market, rows in forecasts.items():
        comparison = compare_paired_baselines(tuple(rows))
        reports[market] = {
            "fixtures": len(comparison.fixture_ids),
            "scores": [
                {
                    "model": score.model_name,
                    "brier": score.brier_score,
                    "log_loss": score.log_loss,
                }
                for score in comparison.scores
            ],
        }
    return reports


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/retrospective-development-report.json")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL_REQUIRED")
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        if connection.info.dbname != "veltrix_ai_analyst":
            raise SystemExit("DATABASE_TARGET_NAME_MISMATCH")
        results, report = load_rows(connection)

    folds = tuple(
        ChronologicalFold(
            train_cutoff=datetime.fromisoformat(cutoff).replace(tzinfo=UTC),
            validation_end=datetime.fromisoformat(cutoff).replace(tzinfo=UTC) + timedelta(days=14),
        )
        for cutoff in (
            "2026-09-15T00:00:00",
            "2026-09-29T00:00:00",
            "2026-10-13T00:00:00",
            "2026-10-27T00:00:00",
        )
    )
    selection = select_hierarchical_hyperparameters(
        results, folds,
        half_lives=(90.0, 180.0, 365.0),
        team_ridges=(0.1, 0.5, 2.0),
        competition_ridges=(0.5, 2.0),
        min_training_fixtures=30,
    )
    rho = estimate_rho_from_development_folds(
        results, folds, selection.selected, min_training_fixtures=30,
    )
    report["development_protocol"] = "EXPANDING_WINDOW_KICKOFF_ORDERED_RETROSPECTIVE_V1"
    report["folds"] = [
        {"train_cutoff": f.train_cutoff.isoformat(), "validation_end": f.validation_end.isoformat()}
        for f in folds
    ]
    report["hyperparameter_selection"] = {
        "protocol": selection.protocol,
        "selected": {
            "half_life_days": selection.selected.half_life_days,
            "team_ridge": selection.selected.team_ridge,
            "competition_ridge": selection.selected.competition_ridge,
        },
        "leaderboard": [
            {
                "half_life_days": s.candidate.half_life_days,
                "team_ridge": s.candidate.team_ridge,
                "competition_ridge": s.candidate.competition_ridge,
                "mean_validation_nll": s.mean_validation_nll,
                "scored_matches": s.scored_matches,
                "folds_scored": s.folds_scored,
            }
            for s in selection.leaderboard
        ],
    }
    report["dixon_coles_rho"] = {
        "rho": rho.rho,
        "development_nll": rho.negative_log_likelihood,
        "out_of_fold_observations": rho.observations,
        "feasible_lower": rho.lower_bound,
        "feasible_upper": rho.upper_bound,
        "protocol": rho.protocol,
    }
    report["paired_baselines"] = evaluate_paired(results, folds, selection.selected, rho.rho)
    report["release_decision"] = "NOT_ELIGIBLE_DEVELOPMENT_ONLY_NO_PROSPECTIVE_PIT_CERTIFICATION"
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
