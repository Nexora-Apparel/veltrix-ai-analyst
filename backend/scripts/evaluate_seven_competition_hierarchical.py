"""Read-only seven-competition hierarchical Poisson/Dixon-Coles development study.

Uses only finished score labels and provider-local IDs. Historical provider
retrieval timestamps are not treated as pre-match feature availability. The
final holdout is later than all tuning/rho-estimation folds.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from math import exp, log
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.models.hierarchical_poisson import (
    HierarchicalGoalResult,
    fit_hierarchical_poisson,
)
from app.models.hierarchical_scoreline import forecast_hierarchical_fixture
from app.models.scoreline import build_scoreline_distribution
from app.validation.binary_market_metrics import (
    BinaryForecast,
    evaluate_paired_binary_market,
)
from app.validation.dixon_coles import estimate_rho_from_development_folds
from app.validation.hierarchical_tuning import (
    ChronologicalFold,
    select_hierarchical_hyperparameters,
)
from app.validation.paired_baselines import (
    ProbabilityForecast,
    compare_paired_baselines,
    evaluate_paired_multiclass,
)
from app.validation.source_provenance import is_valid_retrospective_observation

DATABASE_NAME = "veltrix_ai_analyst"
PROVIDER = "5DollarFootballAPI"
SOURCE_ID = "5dollarfootballapi"
COMPETITIONS = {
    "3118717965": "Brazil Serie A",
    "522514093": "Brazil Serie B",
    "4160026622": "England Premier League",
    "3614399544": "France Ligue 1",
    "686337048": "Germany Bundesliga I",
    "3405541143": "Italy Serie A",
    "4212821298": "Spain La Liga",
}
HOLDOUT_START = datetime(2026, 10, 20, tzinfo=UTC)
DEVELOPMENT_FOLDS = (
    ChronologicalFold(datetime(2026, 9, 15, tzinfo=UTC), datetime(2026, 9, 30, tzinfo=UTC)),
    ChronologicalFold(datetime(2026, 9, 30, tzinfo=UTC), datetime(2026, 10, 10, tzinfo=UTC)),
    ChronologicalFold(datetime(2026, 10, 10, tzinfo=UTC), HOLDOUT_START),
)
CANDIDATE_GRID = {
    "half_lives": (90.0, 180.0, 365.0),
    "team_ridges": (0.5, 2.0, 8.0),
    "competition_ridges": (0.5, 2.0, 8.0),
}
MAX_GOALS = 12


def load_dataset(
    dsn: str,
) -> tuple[list[HierarchicalGoalResult], dict, dict[str, datetime]]:
    """Load and validate the seven scoped competitions in a read-only transaction."""
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        if connection.execute("SELECT current_database() AS n").fetchone()["n"] != DATABASE_NAME:
            raise RuntimeError("DATABASE_TARGET_MISMATCH")
        rows = connection.execute(
            """
            SELECT pf.id::text AS row_id, pf.provider_fixture_id, pf.provider_competition_id,
                   pf.kickoff_at, pf.home_team_provider_id, pf.away_team_provider_id,
                   UPPER(COALESCE(evidence.payload->>'status', 'UNKNOWN')) AS status,
                   NULLIF(evidence.payload->>'home_goals', '')::int AS home_goals,
                   NULLIF(evidence.payload->>'away_goals', '')::int AS away_goals,
                   EXTRACT(YEAR FROM pf.kickoff_at)::int AS calendar_year,
                   evidence.payload->>'season_id' AS provider_season_id,
                   evidence.source_observation_id, evidence.source_sighting_id,
                   evidence.availability_basis, evidence.point_in_time_certifiable,
                   evidence.retrieved_at, evidence.system_observed_at,
                   evidence.response_fetched_at, evidence.response_system_observed_at,
                   evidence.source_published_at, evidence.available_at,
                   evidence.payload_sha256, evidence.provider_response_id,
                   evidence.http_status, evidence.raw_response_sha256
            FROM veltrix_ai_analyst.provider_fixtures pf
            JOIN LATERAL (
                SELECT o.id AS source_observation_id, o.payload,
                       s.id AS source_sighting_id, s.availability_basis,
                       s.point_in_time_certifiable, s.retrieved_at,
                       s.system_observed_at, r.fetched_at AS response_fetched_at,
                       r.system_observed_at AS response_system_observed_at,
                       s.source_published_at, s.available_at,
                       s.payload_sha256, s.provider_response_id,
                       r.http_status, r.response_sha256 AS raw_response_sha256
                FROM veltrix_ai_analyst.source_observations o
                JOIN veltrix_ai_analyst.source_observation_sightings s
                  ON s.source_observation_id = o.id
                JOIN veltrix_ai_analyst.provider_responses r
                  ON r.id = s.provider_response_id
                WHERE o.provider = pf.provider
                  AND o.source_id = pf.source_id
                  AND o.data_type = 'fixtures_and_results'
                  AND o.entity_type = 'fixture'
                  AND o.provider_entity_id = pf.provider_fixture_id
                  AND s.payload_sha256 = o.payload_sha256
                  AND UPPER(COALESCE(o.payload->>'status', 'UNKNOWN'))
                      = UPPER(pf.status)
                  AND UPPER(COALESCE(o.payload->>'status', 'UNKNOWN'))
                      IN ('FINISHED', 'UNKNOWN')
                  AND o.payload->>'competition_id' = pf.provider_competition_id
                  AND o.payload->>'home_team_id' = pf.home_team_provider_id
                  AND o.payload->>'away_team_id' = pf.away_team_provider_id
                  AND NULLIF(o.payload->>'kickoff_at', '')::timestamptz = pf.kickoff_at
                  AND NULLIF(o.payload->>'home_goals', '')::int
                      IS NOT DISTINCT FROM pf.home_goals
                  AND NULLIF(o.payload->>'away_goals', '')::int
                      IS NOT DISTINCT FROM pf.away_goals
                  AND o.payload #>> '{provenance,provider_record_id}' = pf.provider_fixture_id
                ORDER BY s.retrieved_at DESC, s.id DESC
                LIMIT 1
            ) evidence ON TRUE
            WHERE pf.provider = %s AND pf.source_id = %s
              AND pf.provider_competition_id = ANY(%s)
            ORDER BY pf.kickoff_at, pf.provider_fixture_id
            """,
            (PROVIDER, SOURCE_ID, list(COMPETITIONS)),
        ).fetchall()

    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        total_fixture_rows = connection.execute(
            """
            SELECT COUNT(*) AS n
            FROM veltrix_ai_analyst.provider_fixtures
            WHERE provider = %s AND source_id = %s
              AND provider_competition_id = ANY(%s)
            """,
            (PROVIDER, SOURCE_ID, list(COMPETITIONS)),
        ).fetchone()["n"]
    if len(rows) < 998:
        raise RuntimeError(f"INSUFFICIENT_SCOPED_SOURCE_ROWS:{len(rows)}")
    fixture_keys = [(row["provider_competition_id"], row["provider_fixture_id"]) for row in rows]
    if len(fixture_keys) != len(set(fixture_keys)):
        raise RuntimeError("DUPLICATE_PROVIDER_FIXTURE_KEYS")
    invalid = [row for row in rows if not is_valid_retrospective_observation(row)]
    if invalid:
        raise RuntimeError(f"SOURCE_PROVENANCE_AUDIT_FAILED:{len(invalid)}")

    finished = [
        row for row in rows
        if row["status"] == "FINISHED"
        and row["home_goals"] is not None and row["away_goals"] is not None
    ]
    unknown = [
        row for row in rows
        if row["status"] == "UNKNOWN"
        and row["home_goals"] is None and row["away_goals"] is None
    ]
    if len(finished) < 990 or len(unknown) < 8 or len(finished) + len(unknown) != len(rows):
        raise RuntimeError("SOURCE_STATUS_SCORE_AUDIT_MISMATCH")

    label_available_at = {
        f"{row['provider_competition_id']}:{row['provider_fixture_id']}": (
            row["system_observed_at"] or row["retrieved_at"]
        )
        for row in finished
    }
    if any(
        label_available_at[
            f"{row['provider_competition_id']}:{row['provider_fixture_id']}"
        ] <= row["kickoff_at"]
        for row in finished
    ):
        raise RuntimeError("FINISHED_LABEL_AVAILABILITY_MUST_BE_POST_KICKOFF")

    results = [
        HierarchicalGoalResult(
            fixture_id=f"{row['provider_competition_id']}:{row['provider_fixture_id']}",
            kickoff_at=row["kickoff_at"],
            competition_id=row["provider_competition_id"],
            home_team_id=row["home_team_provider_id"],
            away_team_id=row["away_team_provider_id"],
            home_goals=int(row["home_goals"]),
            away_goals=int(row["away_goals"]),
        )
        for row in finished
    ]
    stable = [
        {
            "fixture_id": result.fixture_id,
            "kickoff_at": result.kickoff_at.isoformat(),
            "competition_id": result.competition_id,
            "home_team_id": result.home_team_id,
            "away_team_id": result.away_team_id,
            "home_goals": result.home_goals,
            "away_goals": result.away_goals,
            "source_observation_id": str(row["source_observation_id"]),
            "source_sighting_id": str(row["source_sighting_id"]),
            "provider_response_id": str(row["provider_response_id"]),
            "retrieved_at": row["retrieved_at"].isoformat(),
            "system_observed_at": (
                row["system_observed_at"].isoformat()
                if row["system_observed_at"] is not None else None
            ),
            "response_fetched_at": row["response_fetched_at"].isoformat(),
            "response_system_observed_at": (
                row["response_system_observed_at"].isoformat()
                if row["response_system_observed_at"] is not None else None
            ),
            "availability_basis": row["availability_basis"],
            "payload_sha256": str(row["payload_sha256"]).strip(),
            "raw_response_sha256": str(row["raw_response_sha256"]).strip(),
        }
        for result, row in zip(results, finished, strict=True)
    ]
    fingerprint = hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    provenance = {
        "provider": PROVIDER,
        "source_id": SOURCE_ID,
        "competition_ids": COMPETITIONS,
        "source_rows": len(rows),
        "provider_fixture_rows_total": total_fixture_rows,
        "excluded_fixture_rows_without_matching_settled_sighting": total_fixture_rows - len(rows),
        "calendar_year_fixture_counts": {
            str(year): sum(1 for row in rows if row["calendar_year"] == year)
            for year in sorted({row["calendar_year"] for row in rows})
        },
        "provider_season_id_counts": {
            str(season): sum(1 for row in rows if row["provider_season_id"] == season)
            for season in sorted({row["provider_season_id"] for row in rows if row["provider_season_id"]})
        },
        "provider_season_id_coverage": sum(1 for row in rows if row["provider_season_id"]),
        "per_competition_season_coverage": {
            competition_id: {
                "fixture_rows": sum(1 for row in rows if row["provider_competition_id"] == competition_id),
                "season_ids": {
                    str(season): sum(
                        1 for row in rows
                        if row["provider_competition_id"] == competition_id
                        and row["provider_season_id"] == season
                    )
                    for season in sorted({
                        row["provider_season_id"] for row in rows
                        if row["provider_competition_id"] == competition_id
                        and row["provider_season_id"]
                    })
                },
                "distinct_seasons": len({
                    row["provider_season_id"] for row in rows
                    if row["provider_competition_id"] == competition_id
                    and row["provider_season_id"]
                }),
            }
            for competition_id in sorted(COMPETITIONS)
        },
        "distinct_competition_seasons": sum(
            len({
                row["provider_season_id"] for row in rows
                if row["provider_competition_id"] == competition_id
                and row["provider_season_id"]
            })
            for competition_id in COMPETITIONS
        ),
        "multi_season_competition_count": sum(
            1 for competition_id in COMPETITIONS
            if len({
                row["provider_season_id"] for row in rows
                if row["provider_competition_id"] == competition_id
                and row["provider_season_id"]
            }) > 1
        ),
        "multi_calendar_year_coverage": len({row["calendar_year"] for row in rows}) > 1,
        "source_evidence": [
            {
                "fixture_id": f"{row['provider_competition_id']}:{row['provider_fixture_id']}",
                "provider_competition_id": row["provider_competition_id"],
                "provider_fixture_id": row["provider_fixture_id"],
                "provider_season_id": row["provider_season_id"],
                "home_team_provider_id": row["home_team_provider_id"],
                "away_team_provider_id": row["away_team_provider_id"],
                "kickoff_at": row["kickoff_at"].isoformat(),
                "source_observation_id": str(row["source_observation_id"]),
                "source_sighting_id": str(row["source_sighting_id"]),
                "provider_response_id": str(row["provider_response_id"]),
                "retrieved_at": row["retrieved_at"].isoformat(),
                "response_fetched_at": row["response_fetched_at"].isoformat(),
                "response_system_observed_at": (
                    row["response_system_observed_at"].isoformat()
                    if row["response_system_observed_at"] is not None else None
                ),
                "system_observed_at": (
                    row["system_observed_at"].isoformat()
                    if row["system_observed_at"] is not None else None
                ),
                "availability_basis": row["availability_basis"],
                "payload_sha256": str(row["payload_sha256"]).strip(),
                "raw_response_sha256": str(row["raw_response_sha256"]).strip(),
            }
            for row in rows
        ],
        "finished_labeled_rows": len(finished),
        "unknown_unlabeled_rows_excluded": len(unknown),
        "unknown_fixture_ids": sorted(
            f"{row['provider_competition_id']}:{row['provider_fixture_id']}" for row in unknown
        ),
        "all_observations_retrieved_after_historical_fixtures": all(
            row["retrieved_at"] > row["kickoff_at"] for row in rows
        ),
        "availability_basis_counts": {
            basis: sum(1 for row in rows if row["availability_basis"] == basis)
            for basis in sorted({row["availability_basis"] for row in rows})
        },
        "database_timestamped_capture_rows": sum(
            1 for row in rows if row["system_observed_at"] is not None
        ),
        "pit_certifiable_rows": 0,
        "label_availability_basis_counts": {
            "SYSTEM_OBSERVED_AT": sum(
                1 for row in finished if row["system_observed_at"] is not None
            ),
            "RETRIEVED_AT_ONLY": sum(
                1 for row in finished if row["system_observed_at"] is None
            ),
        },
        "label_availability_min": min(label_available_at.values()).isoformat(),
        "label_availability_max": max(label_available_at.values()).isoformat(),
        "canonical_identity_policy": "PROVIDER_LOCAL_IDS_ONLY_NO_ALIAS_MERGES",
        "feature_policy": "NO_POST_MATCH_RETRIEVED_FEATURES_USED",
        "dataset_fingerprint_sha256": fingerprint,
    }
    if not provenance["all_observations_retrieved_after_historical_fixtures"]:
        raise RuntimeError("HISTORICAL_RETRIEVAL_CHRONOLOGY_AUDIT_FAILED")
    return results, provenance, label_available_at


def outcome(goals_home: int, goals_away: int) -> str:
    if goals_home > goals_away:
        return "HOME"
    if goals_home == goals_away:
        return "DRAW"
    return "AWAY"


def multiclass_metrics(rows: list[dict]) -> dict:
    if not rows:
        raise RuntimeError("EMPTY_EVALUATION_SET")
    brier = 0.0
    log_loss = 0.0
    scoreline_loss = 0.0
    for row in rows:
        probs = row["probabilities"]
        actual = row["outcome"]
        brier += sum((p - (1.0 if label == actual else 0.0)) ** 2 for label, p in probs.items())
        log_loss -= log(max(1e-15, probs[actual]))
        scoreline_loss -= log(max(1e-15, row["scoreline_probability"]))
    n = len(rows)
    return {
        "fixtures": n,
        "brier_1x2": brier / n,
        "log_loss_1x2": log_loss / n,
        "mean_scoreline_log_loss": scoreline_loss / n,
    }


def main() -> int:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise SystemExit("DATABASE_URL_REQUIRED")
    if os.environ.get("EXPECTED_DATABASE_NAME", DATABASE_NAME) != DATABASE_NAME:
        raise SystemExit("EXPECTED_DATABASE_NAME_MISMATCH")

    results, provenance, label_available_at = load_dataset(dsn)
    evaluation_as_of = datetime.now(UTC)
    development = [row for row in results if row.kickoff_at <= HOLDOUT_START]
    holdout = [row for row in results if row.kickoff_at > HOLDOUT_START]
    if len(development) < 100 or len(holdout) < 30:
        raise RuntimeError("INSUFFICIENT_DEVELOPMENT_OR_FINAL_HOLDOUT_ROWS")
    if len({row.fixture_id for row in results}) != len(results):
        raise RuntimeError("DUPLICATE_TRAINING_FIXTURE_IDS")

    fold_availability = []
    for fold in DEVELOPMENT_FOLDS:
        train_rows = [
            row for row in development
            if row.kickoff_at <= fold.train_cutoff
            and label_available_at[row.fixture_id] <= fold.train_cutoff
        ]
        validation_rows = [
            row for row in development
            if fold.train_cutoff < row.kickoff_at <= fold.validation_end
            and label_available_at[row.fixture_id] <= evaluation_as_of
        ]
        fold_availability.append({
            "train_cutoff": fold.train_cutoff.isoformat(),
            "validation_end": fold.validation_end.isoformat(),
            "prior_kickoff_rows": sum(
                1 for row in development if row.kickoff_at <= fold.train_cutoff
            ),
            "training_labels_available_at_cutoff": len(train_rows),
            "validation_labels_available_as_of_evaluation": len(validation_rows),
            "eligible": len(train_rows) >= 60 and bool(validation_rows),
        })
    if not any(item["eligible"] for item in fold_availability):
        report = {
            "report_type": "SEVEN_COMPETITION_HIERARCHICAL_AVAILABILITY_AUDIT",
            "status": "INSUFFICIENT_LABEL_AVAILABILITY_FOR_CHRONOLOGICAL_TUNING",
            "created_at": evaluation_as_of.isoformat(),
            "provenance": provenance,
            "temporal_protocol": {
                "evaluation_as_of": evaluation_as_of.isoformat(),
                "training_label_availability_basis": (
                    "SYSTEM_OBSERVED_AT_WHEN_PRESENT_ELSE_RETRIEVED_AT_ONLY"
                ),
                "retrieved_at_only_labels_are_non_pit": True,
                "folds": fold_availability,
                "historical_pit_certified": False,
            },
            "dataset": {
                "finished_outcome_rows": len(results),
                "development_rows": len(development),
                "event_time_holdout_rows_not_scored": len(holdout),
            },
            "release_decision": {
                "model_fit_performed": False,
                "production_promotion": False,
                "value_betting": "LOCKED",
                "reason": "NO_TRAINING_LABELS_WERE_AVAILABLE_AT_THE_CONFIGURED_FOLD_CUTOFFS",
            },
        }
        canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
        report["report_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        output = Path(os.environ.get(
            "TRAINING_REPORT_PATH",
            "artifacts/seven-competition-hierarchical-availability-audit.json",
        ))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "status": report["status"],
            "report_path": str(output),
            "report_sha256": report["report_sha256"],
            "finished_outcome_rows": len(results),
            "fold_availability": fold_availability,
        }, sort_keys=True))
        return 0

    selection = select_hierarchical_hyperparameters(
        development,
        DEVELOPMENT_FOLDS,
        half_lives=CANDIDATE_GRID["half_lives"],
        team_ridges=CANDIDATE_GRID["team_ridges"],
        competition_ridges=CANDIDATE_GRID["competition_ridges"],
        min_training_fixtures=60,
        label_available_at=label_available_at,
        evaluation_as_of=evaluation_as_of,
    )
    candidate = selection.selected
    rho_estimate = estimate_rho_from_development_folds(
        development,
        DEVELOPMENT_FOLDS,
        candidate,
        min_training_fixtures=60,
        label_available_at=label_available_at,
        evaluation_as_of=evaluation_as_of,
    )

    model = fit_hierarchical_poisson(
        development,
        as_of=HOLDOUT_START,
        half_life_days=candidate.half_life_days,
        team_ridge=candidate.team_ridge,
        competition_ridge=candidate.competition_ridge,
    )
    if not model.optimizer_converged:
        raise RuntimeError("HIERARCHICAL_OPTIMIZER_NOT_CONVERGED")

    # Independent comparator: recency-weighted competition-only home/away scoring rates.
    half_life = candidate.half_life_days
    by_comp: dict[str, list] = {}
    for row in development:
        by_comp.setdefault(row.competition_id, []).append(row)
    global_rows = development
    def weighted_rates(rows):
        weights = [
            exp(-0.6931471805599453 * max(0.0, (HOLDOUT_START-row.kickoff_at).total_seconds()/86400) / half_life)
            for row in rows
        ]
        total = sum(weights)
        return (
            max(0.05, sum(w*r.home_goals for w, r in zip(weights, rows))/total),
            max(0.05, sum(w*r.away_goals for w, r in zip(weights, rows))/total),
        )

    model_rows: list[dict] = []
    baseline_rows: list[dict] = []
    paired: list[ProbabilityForecast] = []
    model_btts: list[BinaryForecast] = []
    baseline_btts: list[BinaryForecast] = []
    model_over25: list[BinaryForecast] = []
    baseline_over25: list[BinaryForecast] = []
    for target in holdout:
        forecast = forecast_hierarchical_fixture(
            model, target.home_team_id, target.away_team_id, target.competition_id,
            rho=rho_estimate.rho, max_goals=MAX_GOALS,
        )
        model_dist = forecast.scoreline
        model_probs = {
            "HOME": model_dist.home_win, "DRAW": model_dist.draw, "AWAY": model_dist.away_win,
        }
        score_prob = (
            model_dist.probabilities[target.home_goals][target.away_goals]
            if target.home_goals <= MAX_GOALS and target.away_goals <= MAX_GOALS else 1e-15
        )
        model_rows.append({
            "fixture_id": target.fixture_id, "outcome": outcome(target.home_goals,target.away_goals),
            "probabilities": model_probs, "scoreline_probability": score_prob,
        })
        rates = weighted_rates(by_comp.get(target.competition_id, global_rows))
        baseline_dist = build_scoreline_distribution(*rates, rho=0.0, max_goals=MAX_GOALS)
        baseline_probs = {
            "HOME": baseline_dist.home_win, "DRAW": baseline_dist.draw, "AWAY": baseline_dist.away_win,
        }
        baseline_score_prob = (
            baseline_dist.probabilities[target.home_goals][target.away_goals]
            if target.home_goals <= MAX_GOALS and target.away_goals <= MAX_GOALS else 1e-15
        )
        baseline_rows.append({
            "fixture_id": target.fixture_id, "outcome": outcome(target.home_goals,target.away_goals),
            "probabilities": baseline_probs, "scoreline_probability": baseline_score_prob,
        })
        actual_btts = target.home_goals > 0 and target.away_goals > 0
        actual_over25 = target.home_goals + target.away_goals > 2
        model_btts.append(BinaryForecast(
            target.fixture_id, target.competition_id, actual_btts, model_dist.btts_yes
        ))
        baseline_btts.append(BinaryForecast(
            target.fixture_id, target.competition_id, actual_btts, baseline_dist.btts_yes
        ))
        model_over25.append(BinaryForecast(
            target.fixture_id, target.competition_id, actual_over25, model_dist.over(2.5)
        ))
        baseline_over25.append(BinaryForecast(
            target.fixture_id, target.competition_id, actual_over25, baseline_dist.over(2.5)
        ))
        paired.extend((
            ProbabilityForecast(
                target.fixture_id,
                "HIERARCHICAL_POISSON_DIXON_COLES",
                model_probs,
                outcome(target.home_goals, target.away_goals),
                target.competition_id,
            ),
            ProbabilityForecast(
                target.fixture_id,
                "COMPETITION_ONLY_POISSON",
                baseline_probs,
                outcome(target.home_goals, target.away_goals),
                target.competition_id,
            ),
        ))

    paired_comparison = compare_paired_baselines(tuple(paired))
    paired_1x2_confidence = evaluate_paired_multiclass(
        tuple(paired),
        model_name="HIERARCHICAL_POISSON_DIXON_COLES",
        baseline_name="COMPETITION_ONLY_POISSON",
        bootstrap_replicates=2000,
        seed=20261118,
    )
    btts_evaluation = evaluate_paired_binary_market(
        model_btts, baseline_btts, bootstrap_replicates=2000, seed=20261119
    )
    over25_evaluation = evaluate_paired_binary_market(
        model_over25, baseline_over25, bootstrap_replicates=2000, seed=20261120
    )
    report = {
        "report_type": "SEVEN_COMPETITION_RETROSPECTIVE_DEVELOPMENT_EVALUATION",
        "status": "RESEARCH_ONLY_NOT_PRODUCTION_APPROVAL",
        "created_at": datetime.now(UTC).isoformat(),
        "provenance": provenance,
        "temporal_protocol": {
            "training_cutoff": HOLDOUT_START.isoformat(),
            "development_folds": [
                {"train_cutoff": fold.train_cutoff.isoformat(), "validation_end": fold.validation_end.isoformat()}
                for fold in DEVELOPMENT_FOLDS
            ],
            "final_holdout_rule": "KICKOFF_STRICTLY_AFTER_2026-10-20T00:00:00Z",
            "simultaneous_kickoff_isolation": "DATE_BOUNDARIES_NOT_SPLITTING_IDENTICAL_KICKOFF_TIMES",
            "historical_pit_certified": False,
        },
        "tuning": {
            "protocol": selection.protocol,
            "candidate_grid": CANDIDATE_GRID,
            "selected": {
                "half_life_days": candidate.half_life_days,
                "team_ridge": candidate.team_ridge,
                "competition_ridge": candidate.competition_ridge,
            },
            "leaderboard": [
                {
                    "half_life_days": row.candidate.half_life_days,
                    "team_ridge": row.candidate.team_ridge,
                    "competition_ridge": row.candidate.competition_ridge,
                    "mean_validation_poisson_nll": row.mean_validation_nll,
                    "scored_matches": row.scored_matches,
                    "folds_scored": row.folds_scored,
                } for row in selection.leaderboard
            ],
        },
        "dixon_coles": {
            "protocol": rho_estimate.protocol,
            "rho": rho_estimate.rho,
            "negative_log_likelihood": rho_estimate.negative_log_likelihood,
            "development_oof_observations": rho_estimate.observations,
            "feasible_interval": [rho_estimate.lower_bound, rho_estimate.upper_bound],
        },
        "optimizer": {
            "converged": model.optimizer_converged,
            "iterations": model.optimizer_iterations,
            "gradient_norm": model.optimizer_gradient_norm,
            "development_fixtures": len(development),
            "distinct_provider_team_ids": len(model.team_match_counts),
            "competitions": len(model.competition_match_counts),
        },
        "holdout": {
            "start_exclusive": HOLDOUT_START.isoformat(),
            "end_inclusive": max(row.kickoff_at for row in holdout).isoformat(),
            "model": multiclass_metrics(model_rows),
            "independent_competition_only_baseline": multiclass_metrics(baseline_rows),
            "paired_comparison": {
                "protocol": paired_comparison.protocol,
                "fixture_count": len(paired_comparison.fixture_ids),
                "scores": [
                    {"model": score.model_name, "fixtures": score.fixtures,
                     "brier_score": score.brier_score, "log_loss": score.log_loss}
                    for score in paired_comparison.scores
                ],
            },
            "one_x_two_confidence_and_competition_breakdown": paired_1x2_confidence,
            "independent_binary_markets": {
                "evaluation_basis": "RETROSPECTIVE_NON_PIT_RESEARCH_ONLY",
                "BTTS": btts_evaluation,
                "OVER_UNDER_2_5": over25_evaluation,
            },
        },
        "release_decision": {
            "production_promotion": False,
            "value_betting": "LOCKED",
            "reason": "RETROSPECTIVE_NON_PIT_CORPUS_AND_LIMITED_SINGLE_SEASON_HOLDOUT",
        },
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["report_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    output = Path(os.environ.get("TRAINING_REPORT_PATH", "artifacts/six-competition-hierarchical-report.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "SEVEN_COMPETITION_RETROSPECTIVE_EVALUATION_COMPLETE",
        "report_path": str(output),
        "report_sha256": report["report_sha256"],
        "development_fixtures": len(development),
        "holdout_fixtures": len(holdout),
        "selected_candidate": report["tuning"]["selected"],
        "rho": rho_estimate.rho,
        "paired_comparison": report["holdout"]["paired_comparison"],
        "production_promotion": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
