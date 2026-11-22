"""Stage 7 selected Newton model, research-only inference and slate safety monitor."""
from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from app.models.hierarchical_poisson import fit_hierarchical_poisson
from app.research.prospective_shadow import (
    _training_data_sha256,
    select_training_rows,
)
from app.validation.prospective_model_evaluation import _goal_result

MODEL_VERSION = "hierarchical-poisson-newton-shadow-v2"
MIN_TEAM_HISTORY = 5
OUTCOMES = ("HOME", "DRAW", "AWAY")



def build_run_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Build the sanitized, stable summary artifact for one Stage 7 run."""
    monitor = report.get("concentration_monitor", {})
    sanitized = report.get("sanitized_summary", {})
    return {
        "status": report["status"],
        "model_version": report["model"]["version"],
        "fixtures_considered": sanitized.get("fixtures_considered", 0),
        "fitted_fixture_count": sanitized.get("fitted", 0),
        "shown_fixture_count": sanitized.get("shown", 0),
        "fixture_count": report.get("forecast_count", 0),
        "p_home_mean": monitor.get("p_home_mean"),
        "p_home_min": monitor.get("p_home_min"),
        "p_home_max": monitor.get("p_home_max"),
        "expected_goals_sd": sanitized.get("expected_goals_sd"),
        "p_draw_above_050_share": monitor.get("p_draw_above_050_share"),
        "any_probability_above_080_share": monitor.get("any_probability_above_080_share"),
        "monitor_status": "QUARANTINED" if monitor.get("quarantined", False) else "PASS",
        "extreme_forecasts": sanitized.get("extremes"),
        "abstention_count": report.get("abstention_count", 0),
        "p_home_sd": monitor.get("p_home_sd"),
        "top_pick_shares": monitor.get("top_pick_shares"),
        "concentration_quarantined": monitor.get("quarantined", False),
        "concentration_violations": monitor.get("violations", []),
        "certification": report["certification"],
        "research_label": report["research_label"],
        "provider_calls": report.get("provider_calls", 0),
        "odds_used": report.get("odds_used", False),
        "production_promotion": report["production_promotion"],
        "value_betting": report["value_betting"],
        "sample_forecasts": [
            {
                "home_team": prediction.get("home_team"),
                "away_team": prediction.get("away_team"),
                "competition": prediction.get("competition"),
                "p_home": prediction["markets"]["1X2"]["HOME"],
                "p_draw": prediction["markets"]["1X2"]["DRAW"],
                "p_away": prediction["markets"]["1X2"]["AWAY"],
                "btts_yes": prediction["markets"]["BTTS"]["YES"],
                "over_2_5": prediction["markets"]["TOTALS_2_5"]["OVER"],
            }
            for prediction in report.get("predictions", [])[:5]
        ],
    }


def insufficient_team_history(home_matches: int, away_matches: int) -> bool:
    return home_matches < MIN_TEAM_HISTORY or away_matches < MIN_TEAM_HISTORY


def _pmf(rate: float, cap: int = 24) -> list[float]:
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("INVALID_EXPECTED_GOALS")
    values = [math.exp(-rate)]
    for goal in range(1, cap + 1):
        values.append(values[-1] * rate / goal)
    total = sum(values)
    return [value / total for value in values]


def _markets(home_rate: float, away_rate: float) -> dict[str, dict[str, float]]:
    home, away = _pmf(home_rate), _pmf(away_rate)
    result = dict.fromkeys(OUTCOMES, 0.0)
    totals = [0.0] * 50
    for hg, hp in enumerate(home):
        for ag, ap in enumerate(away):
            mass = hp * ap
            result["HOME" if hg > ag else "DRAW" if hg == ag else "AWAY"] += mass
            totals[hg + ag] += mass
    one_x_two_sum = sum(result.values())
    one_x_two = {key: value / one_x_two_sum for key, value in result.items()}
    btts_yes = (1.0 - home[0]) * (1.0 - away[0])
    over = {
        "TOTALS_1_5": sum(totals[2:]),
        "TOTALS_2_5": sum(totals[3:]),
        "TOTALS_3_5": sum(totals[4:]),
    }
    return {
        "1X2": one_x_two,
        "BTTS": {"YES": btts_yes, "NO": 1.0 - btts_yes},
        **{
            market: {"OVER": value, "UNDER": 1.0 - value}
            for market, value in over.items()
        },
    }


def _summary(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(predictions)
    if not n:
        return {
            "fixture_count": 0,
            "p_home_sd": 0.0,
            "top_pick_shares": {},
            "p_draw_above_050_share": 0.0,
            "any_probability_above_080_share": 0.0,
        }
    p_home = [float(p["markets"]["1X2"]["HOME"]) for p in predictions]
    mean = sum(p_home) / n
    sd = math.sqrt(sum((value - mean) ** 2 for value in p_home) / n)
    top = {
        "1X2": max(
            (sum(max(p["markets"]["1X2"], key=p["markets"]["1X2"].get) == outcome
                 for p in predictions) / n for outcome in OUTCOMES),
            default=0.0,
        )
    }
    # Expose each outcome share, not only the maximum.
    top["1X2_by_outcome"] = {
        outcome: sum(
            max(p["markets"]["1X2"], key=p["markets"]["1X2"].get) == outcome
            for p in predictions
        ) / n
        for outcome in OUTCOMES
    }
    top["BTTS_yes"] = sum(
        max(p["markets"]["BTTS"], key=p["markets"]["BTTS"].get) == "YES"
        for p in predictions
    ) / n
    top["Over_2_5"] = sum(
        max(p["markets"]["TOTALS_2_5"], key=p["markets"]["TOTALS_2_5"].get) == "OVER"
        for p in predictions
    ) / n
    return {
        "fixture_count": n,
        "p_home_mean": mean,
        "p_home_sd": sd,
        "p_home_min": min(p_home),
        "p_home_max": max(p_home),
        "top_pick_shares": top,
        "p_draw_above_050_share": sum(
            p["markets"]["1X2"]["DRAW"] > 0.50 for p in predictions
        ) / n,
        "any_probability_above_080_share": sum(
            any(
                value > 0.80
                for market in p["markets"].values()
                for value in market.values()
            )
            for p in predictions
        ) / n,
    }


def concentration_violations(summary: dict[str, Any]) -> list[str]:
    n = int(summary.get("fixture_count", 0))
    if n < 15:
        return []
    shares = summary["top_pick_shares"]
    violations = []
    if summary["p_home_sd"] < 0.08 or summary["p_home_sd"] > 0.22:
        violations.append("P_HOME_SD_OUTSIDE_0_08_0_22")
    if max(shares["1X2_by_outcome"].values()) > 0.85:
        violations.append("SINGLE_1X2_OUTCOME_TOP_PICK_OVER_85_PERCENT")
    if shares["BTTS_yes"] > 0.90:
        violations.append("BTTS_YES_PICK_SHARE_OVER_90_PERCENT")
    if shares["Over_2_5"] > 0.90:
        violations.append("OVER_2_5_PICK_SHARE_OVER_90_PERCENT")
    return violations


def build_stage7_shadow_predictions(
    dataset: dict[str, Any],
    *,
    generated_at: datetime | None = None,
    max_fixtures: int = 25,
    max_snapshot_age_hours: float = 6.0,
) -> dict[str, Any]:
    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None or generated.utcoffset() is None:
        raise ValueError("GENERATED_AT_MUST_BE_TIMEZONE_AWARE")
    rows = tuple(dataset.get("rows") or ())
    training_only = tuple(dataset.get("training_only_rows") or ())
    targets = sorted(
        (
            row for row in rows
            if row.validation_eligible and row.label is None
            and row.prediction_cutoff_at is not None
            and row.canonical_fixture_id and row.canonical_competition_id
            and row.prediction_cutoff_at <= generated
            and row.prediction_cutoff_at < row.kickoff_at
            and row.kickoff_at > generated
            and (generated - row.prediction_cutoff_at).total_seconds()
                <= max_snapshot_age_hours * 3600
        ),
        key=lambda row: (row.kickoff_at, row.fixture_id),
    )[:max_fixtures]
    base = {
        "generated_at": generated.isoformat(),
        "status": "NO_FRESH_UPCOMING_SNAPSHOTS",
        "research_only": True,
        "research_label": "RESEARCH ONLY",
        "certification": "RETROSPECTIVE_NOT_PIT_CERTIFIED",
        "dataset_sha256": dataset["dataset_sha256"],
        "training_fixture_count": 0,
        "training_cutoff_at": None,
        "training_data_sha256": None,
        "model": {"family": "HIERARCHICAL_POISSON", "version": MODEL_VERSION},
        "forecast_count": 0,
        "abstention_count": 0,
        "predictions": [],
        "abstentions": [],
        "concentration_monitor": {
            "fitted_fixture_count": 0,
            "retained_fixture_count": 0,
            "abstained_fixture_count": 0,
        },
        "provider_calls": 0,
        "database_writes": 0,
        "odds_used": False,
        "production_promotion": "LOCKED",
        "release_eligible": False,
        "value_betting": "LOCKED",
    }
    if not targets:
        return base

    common_cutoff = min(row.prediction_cutoff_at for row in targets)
    training = select_training_rows(
        training_only, rows, prediction_cutoff_at=common_cutoff
    )
    if not training:
        base["status"] = "INSUFFICIENT_CUTOFF_VALID_TRAINING_LABELS"
        return base
    training_cutoff = max(row.label_observed_at for row in training)
    weights = []
    for row in training:
        age_days = max(0.0, (training_cutoff - row.kickoff_at).total_seconds() / 86400)
        weights.append(math.exp(-math.log(2.0) * age_days / 730.0))
    total_weight = sum(weights)
    weighted_goals = sum(
        w * (int(row.label["home_goals"]) + int(row.label["away_goals"]))
        for w, row in zip(weights, training)
    )
    mu = weighted_goals / (2.0 * total_weight)
    model = fit_hierarchical_poisson(
        [_goal_result(row) for row in training],
        as_of=training_cutoff,
        half_life_days=730.0,
        team_ridge=4.0 * mu / total_weight,
        competition_ridge=8.0 * mu / total_weight,
        optimizer="newton",
        max_iterations=200,
        tolerance=1e-7,
    )
    if not model.optimizer_converged:
        base["status"] = "NO_VALID_SHADOW_FORECASTS"
        base["abstentions"] = [{"reason": "NEWTON_FIT_NOT_CONVERGED"}]
        base["abstention_count"] = 1
        return base

    training_sha = _training_data_sha256(training)
    fitted_predictions, predictions, abstentions = [], [], []
    for row in targets:
        rates = model.predict(
            row.home_team_id, row.away_team_id, row.competition_id
        )
        markets = _markets(rates.home_lambda, rates.away_lambda)
        fitted = {
            "canonical_fixture_id": str(row.canonical_fixture_id),
            "canonical_competition_id": str(row.canonical_competition_id),
            "home_canonical_team_id": str(row.home_team_id),
            "away_canonical_team_id": str(row.away_team_id),
            "kickoff_at": row.kickoff_at.isoformat(),
            "prediction_cutoff_at": row.prediction_cutoff_at.isoformat(),
            "generated_at": generated.isoformat(),
            "training_cutoff_at": training_cutoff.isoformat(),
            "training_fixture_count": len(training),
            "training_data_sha256": training_sha,
            "expected_home_goals": rates.home_lambda,
            "expected_away_goals": rates.away_lambda,
            "markets": markets,
            "team_history": {
                "home_matches": rates.home_team_history,
                "away_matches": rates.away_team_history,
            },
            "publication_status": "NOT_PUBLISHED",
            "value_betting_status": "LOCKED",
        }
        fitted_predictions.append(fitted)
        if insufficient_team_history(rates.home_team_history, rates.away_team_history):
            abstentions.append({
                "canonical_fixture_id": str(row.canonical_fixture_id),
                "reason": "ABSTAIN_INSUFFICIENT_TEAM_HISTORY",
                "home_team_matches": rates.home_team_history,
                "away_team_matches": rates.away_team_history,
            })
        else:
            predictions.append(fitted)
    # Safety monitor applies to all fitted fixtures, including subsequently abstained ones.
    monitor = _summary(fitted_predictions)
    violations = concentration_violations(monitor)
    shown = predictions if not violations else []
    expected_total = [
        p["expected_home_goals"] + p["expected_away_goals"]
        for p in fitted_predictions
    ]
    if expected_total:
        mean_total = sum(expected_total) / len(expected_total)
        expected_goals_sd = math.sqrt(
            sum((value - mean_total) ** 2 for value in expected_total) / len(expected_total)
        )
    else:
        expected_goals_sd = 0.0
    extreme = {
        "highest_p_home": max(fitted_predictions, key=lambda p:p["markets"]["1X2"]["HOME"], default=None),
        "highest_p_away": max(fitted_predictions, key=lambda p:p["markets"]["1X2"]["AWAY"], default=None),
        "highest_p_draw": max(fitted_predictions, key=lambda p:p["markets"]["1X2"]["DRAW"], default=None),
    }
    base["sanitized_summary"] = {
        "fixtures_considered": len(targets),
        "abstained": len(abstentions),
        "fitted": len(fitted_predictions),
        "shown": len(shown),
        "p_home_mean": monitor.get("p_home_mean"),
        "p_home_sd": monitor.get("p_home_sd"),
        "p_home_min": monitor.get("p_home_min"),
        "p_home_max": monitor.get("p_home_max"),
        "expected_goals_sd": expected_goals_sd,
        "top_pick_shares": monitor.get("top_pick_shares"),
        "p_draw_above_050_share": monitor.get("p_draw_above_050_share"),
        "any_probability_above_080_share": monitor.get("any_probability_above_080_share"),
        "monitor_status": "QUARANTINED" if violations else "PASS",
        "five_samples": shown[:5],
        "extremes": extreme,
    }
    base.update({
        "status": "SHADOW_FORECASTS_READY" if predictions and not violations
                  else "NO_VALID_SHADOW_FORECASTS",
        "training_fixture_count": len(training),
        "training_cutoff_at": training_cutoff.isoformat(),
        "training_data_sha256": training_sha,
        "model": {
            "family": "HIERARCHICAL_POISSON",
            "version": MODEL_VERSION,
            "k": 4.0,
            "half_life_days": 730.0,
            "blend_weight": 1.0,
            "solver": "DAMPED_NEWTON",
            "optimizer_converged": True,
            "optimizer_iterations": model.optimizer_iterations,
            "optimizer_gradient_norm": model.optimizer_gradient_norm,
            "optimizer_relative_objective_change": model.optimizer_relative_objective_change,
        },
        "predictions": shown,
        "abstentions": abstentions,
        "forecast_count": len(shown),
        "abstention_count": len(abstentions),
        "concentration_monitor": {
            **monitor,
            "thresholds": {
                "minimum_slate_size": 15,
                "p_home_sd": [0.08, 0.22],
                "single_1x2_top_pick_share_max": 0.85,
                "btts_yes_pick_share_max": 0.90,
                "over_2_5_pick_share_max": 0.90,
            },
            "quarantined": bool(violations),
            "violations": violations,
        },
    })
    if not predictions and not violations:
        base["status"] = "NO_VALID_SHADOW_FORECASTS"
    return base
