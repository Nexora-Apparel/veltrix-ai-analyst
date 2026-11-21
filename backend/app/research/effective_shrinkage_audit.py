"""Per-team effective-shrinkage audit for an archived shadow fit.

This is a descriptive fit audit, not predictive evaluation or admission.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from math import exp, log
from pathlib import Path
from statistics import median
from typing import Any

from app.models.hierarchical_poisson import (
    HierarchicalGoalResult,
    fit_hierarchical_poisson,
)
from app.research.shadow_model_audit import reproduce_shadow_fit


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def effective_shrinkage_report(
    dataset: dict[str, Any], forecast: dict[str, Any]
) -> dict[str, Any]:
    """Report per-team fitted/reference ratios and prior/data information."""
    reproduction = reproduce_shadow_fit(dataset, forecast)
    rows = dataset["training_only_rows"]
    model_meta = forecast["model"]
    cutoff = _aware(forecast["training_cutoff_at"])
    half_life = float(model_meta["half_life_days"])
    team_ridge = float(model_meta["team_ridge"])
    competition_ridge = float(model_meta["competition_ridge"])

    results = [
        HierarchicalGoalResult(
            fixture_id=str(row["fixture_id"]),
            kickoff_at=_aware(row["kickoff_at"]),
            competition_id=str(row["competition_id"]),
            home_team_id=str(row["home_team_id"]),
            away_team_id=str(row["away_team_id"]),
            home_goals=int(row["label"]["home_goals"]),
            away_goals=int(row["label"]["away_goals"]),
        )
        for row in rows
    ]
    fitted = fit_hierarchical_poisson(
        results,
        as_of=cutoff,
        half_life_days=half_life,
        team_ridge=team_ridge,
        competition_ridge=competition_ridge,
    )
    # 1e-9 is the numerical zero-penalty limit for this optimizer.
    reference = fit_hierarchical_poisson(
        results,
        as_of=cutoff,
        half_life_days=half_life,
        team_ridge=1e-9,
        competition_ridge=1e-9,
    )

    weights = [
        exp(-log(2.0) * max(
            0.0, (cutoff - _aware(row["kickoff_at"])).total_seconds() / 86400.0
        ) / half_life)
        for row in rows
    ]
    total_weight = sum(weights)
    tau = team_ridge * total_weight
    attack_information = {team: 0.0 for team in fitted.attack}
    defence_information = {team: 0.0 for team in fitted.defence}

    for row, weight in zip(rows, weights):
        rates = fitted.predict(
            row["home_team_id"], row["away_team_id"], row["competition_id"]
        )
        # Poisson Fisher information for a log-rate parameter is its expected rate.
        attack_information[row["home_team_id"]] += weight * rates.home_lambda
        attack_information[row["away_team_id"]] += weight * rates.away_lambda
        defence_information[row["away_team_id"]] += weight * rates.home_lambda
        defence_information[row["home_team_id"]] += weight * rates.away_lambda

    team_rows = []
    for team in sorted(fitted.attack):
        ref_attack = reference.attack[team]
        ref_defence = reference.defence[team]
        team_rows.append({
            "team_id": team,
            "attack_fitted": fitted.attack[team],
            "attack_near_unpenalized": ref_attack,
            "attack_effect_ratio": (
                fitted.attack[team] / ref_attack if abs(ref_attack) > 1e-8 else None
            ),
            "defence_fitted": fitted.defence[team],
            "defence_near_unpenalized": ref_defence,
            "defence_effect_ratio": (
                fitted.defence[team] / ref_defence if abs(ref_defence) > 1e-8 else None
            ),
            "attack_tau_to_data_information": tau / attack_information[team],
            "defence_tau_to_data_information": tau / defence_information[team],
            "attack_data_information": attack_information[team],
            "defence_data_information": defence_information[team],
        })

    attack_ratios = [
        abs(row["attack_effect_ratio"]) for row in team_rows
        if row["attack_effect_ratio"] is not None
    ]
    defence_ratios = [
        abs(row["defence_effect_ratio"]) for row in team_rows
        if row["defence_effect_ratio"] is not None
    ]
    return {
        "status": "EFFECTIVE_SHRINKAGE_AUDIT_COMPLETE",
        "evaluation_type": "RETROSPECTIVE_FIT_DIAGNOSTIC_NOT_PREDICTIVE_EVALUATION",
        "training_fixture_count": len(rows),
        "team_count": len(team_rows),
        "competition_count": len(fitted.competition_effects),
        "effective_runtime": {
            "team_ridge": team_ridge,
            "competition_ridge": competition_ridge,
            "half_life_days": half_life,
            "total_recency_weight": total_weight,
            "summed_objective_team_tau": tau,
            "near_unpenalized_reference_ridge": 1e-9,
        },
        "attack_absolute_effect_ratio_median": median(attack_ratios),
        "defence_absolute_effect_ratio_median": median(defence_ratios),
        "attack_tau_to_data_information_median": median(
            row["attack_tau_to_data_information"] for row in team_rows
        ),
        "defence_tau_to_data_information_median": median(
            row["defence_tau_to_data_information"] for row in team_rows
        ),
        "teams": team_rows,
        "fit_reproduction": reproduction["status"],
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--forecast", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    forecast = json.loads(args.forecast.read_text(encoding="utf-8"))
    report = effective_shrinkage_report(dataset, forecast)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        key: value for key, value in report.items() if key != "teams"
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
