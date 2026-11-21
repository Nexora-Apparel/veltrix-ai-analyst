from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.models.hierarchical_poisson import fit_hierarchical_poisson
from app.research.corrected_shrinkage_audit import _dt, _result
from app.research.shrinkage_repair_metrics import (
    blend_probabilities,
    evaluation_diagnostics,
    paired_date_block_bootstrap,
)

OUTCOMES = ("HOME", "DRAW", "AWAY")
FOLD_START_PERCENTAGES = (60, 70, 80, 90)
RETROSPECTIVE_STATUS = "RETROSPECTIVE_NOT_PIT_CERTIFIED"


def _sha256_config(config: dict[str, Any]) -> str:
    canonical = json.dumps(
        config, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _poisson_rate_probabilities(home_rate: float, away_rate: float) -> dict[str, float]:
    def pmf(rate: float, cap: int = 24) -> list[float]:
        values = [math.exp(-rate)]
        for index in range(1, cap + 1):
            values.append(values[-1] * rate / index)
        return values

    home, away = pmf(home_rate), pmf(away_rate)
    result = dict.fromkeys(OUTCOMES, 0.0)
    for home_goals, home_probability in enumerate(home):
        for away_goals, away_probability in enumerate(away):
            outcome = "HOME" if home_goals > away_goals else (
                "DRAW" if home_goals == away_goals else "AWAY"
            )
            result[outcome] += home_probability * away_probability
    total = sum(result.values())
    if total <= 0 or not math.isfinite(total):
        raise ArithmeticError("invalid Poisson scoreline probability mass")
    return {key: value / total for key, value in result.items()}


def _actual(row: dict[str, Any]) -> str:
    home = int(row["label"]["home_goals"])
    away = int(row["label"]["away_goals"])
    return "HOME" if home > away else ("DRAW" if home == away else "AWAY")


def _log_loss(rows: list[dict[str, Any]]) -> float:
    return -sum(
        math.log(max(1e-15, float(row["probabilities"][_actual(row)]))) for row in rows
    ) / len(rows)


def _brier(rows: list[dict[str, Any]]) -> float:
    return sum(
        sum(
            (float(row["probabilities"][outcome]) - float(_actual(row) == outcome)) ** 2
            for outcome in OUTCOMES
        )
        for row in rows
    ) / len(rows)


def _time_weight(row: dict[str, Any], cutoff: datetime, half_life: float) -> float:
    age_days = max(0.0, (cutoff - _dt(row["kickoff_at"])).total_seconds() / 86400.0)
    return math.exp(-math.log(2.0) * age_days / half_life)


def _folds(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dates = sorted({_dt(row["kickoff_at"]).date().isoformat() for row in rows})
    result = []
    for fold_number, percentage in enumerate(FOLD_START_PERCENTAGES, start=1):
        cut = max(1, min(len(dates) - 1, math.floor(len(dates) * percentage / 100)))
        end = min(len(dates), cut + max(1, math.ceil(len(dates) * 0.10)))
        test_dates = set(dates[cut:end])
        test = [row for row in rows if _dt(row["kickoff_at"]).date().isoformat() in test_dates]
        if not test:
            raise ValueError(f"EMPTY_TEST_WINDOW:fold_{fold_number}")
        cutoff = min(_dt(row["kickoff_at"]) for row in test)
        # label_observed_at is bulk-ingestion time, not the historical availability proxy.
        train = [
            row for row in rows
            if _dt(row["kickoff_at"]) + timedelta(hours=3) < cutoff
        ]
        if not train:
            raise ValueError(f"EMPTY_RETROSPECTIVE_TRAINING_WINDOW:fold_{fold_number}")
        if any(_dt(row["kickoff_at"]) >= cutoff for row in train):
            raise ValueError(f"TRAINING_KICKOFF_AT_OR_AFTER_CUTOFF:fold_{fold_number}")
        result.append({
            "fold": fold_number,
            "training_start_date": min(_dt(row["kickoff_at"]).date().isoformat() for row in train),
            "training_end_date": max(_dt(row["kickoff_at"]).date().isoformat() for row in train),
            "test_start_date": min(test_dates),
            "test_end_date": max(test_dates),
            "cutoff": cutoff,
            "train": train,
            "test": test,
        })
    return result


def _climatology(train: list[dict[str, Any]], cutoff: datetime) -> dict[str, float]:
    counts = dict.fromkeys(OUTCOMES, 0.0)
    for row in train:
        counts[_actual(row)] += _time_weight(row, cutoff, 365.0)
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("EMPTY_CLIMATOLOGY_BASELINE")
    return {outcome: counts[outcome] / total for outcome in OUTCOMES}


def _plain_scaled_poisson(
    train: list[dict[str, Any]], cutoff: datetime, half_life: float
) -> tuple[float, float]:
    weighted = [(_time_weight(row, cutoff, half_life), row) for row in train]
    total = sum(weight for weight, _ in weighted)
    if total <= 0:
        raise ValueError("EMPTY_PLAIN_POISSON_BASELINE")
    home = sum(weight * int(row["label"]["home_goals"]) for weight, row in weighted) / total
    away = sum(weight * int(row["label"]["away_goals"]) for weight, row in weighted) / total
    return home, away


def _dispersion(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def summary(values: list[float]) -> dict[str, float]:
        mean = sum(values) / len(values)
        return {
            "mean": mean,
            "sd": math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)),
            "min": min(values),
            "max": max(values),
        }

    return {
        "expected_home_goals": summary([row["expected_home_goals"] for row in rows]),
        "expected_away_goals": summary([row["expected_away_goals"] for row in rows]),
        "p_home": summary([row["probabilities"]["HOME"] for row in rows]),
        "n": len(rows),
    }


def _comparison(
    model_rows: list[dict[str, Any]], baseline_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    paired = []
    for model, baseline in zip(model_rows, baseline_rows):
        actual = _actual(model)
        difference = (
            -math.log(max(1e-15, model["probabilities"][actual]))
            + math.log(max(1e-15, baseline["probabilities"][actual]))
        )
        paired.append((_dt(model["kickoff_at"]).date().isoformat(), difference))
    return paired_date_block_bootstrap(paired, replicates=2000, seed=20261121)


def _score_rows(
    test: list[dict[str, Any]],
    model: Any,
    climatology: dict[str, float],
    plain_rates: tuple[float, float],
    blend_weight: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    plain_probabilities = _poisson_rate_probabilities(*plain_rates)
    model_rows, climate_rows, plain_rows = [], [], []
    for row in test:
        rates = model.predict(
            str(row["home_team_id"]), str(row["away_team_id"]), str(row["competition_id"])
        )
        raw = _poisson_rate_probabilities(rates.home_lambda, rates.away_lambda)
        probabilities = blend_probabilities(raw, climatology, blend_weight)
        common = {
            "competition_id": str(row.get("canonical_competition_id", row["competition_id"])),
            "kickoff_at": row["kickoff_at"],
            "label": row["label"],
        }
        model_rows.append({
            **common,
            "probabilities": probabilities,
            "expected_home_goals": float(rates.home_lambda),
            "expected_away_goals": float(rates.away_lambda),
        })
        climate_rows.append({**common, "probabilities": climatology})
        plain_rows.append({**common, "probabilities": plain_probabilities})
    return model_rows, climate_rows, plain_rows


def _fit_and_score(
    train: list[dict[str, Any]],
    test: list[dict[str, Any]],
    cutoff: datetime,
    k: float,
    half_life: float,
    blend_weight: float,
    config: dict[str, Any],
) -> tuple[Any, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    weights = [_time_weight(row, cutoff, half_life) for row in train]
    total_weight = sum(weights)
    weighted_goals = sum(
        weight * (int(row["label"]["home_goals"]) + int(row["label"]["away_goals"]))
        for row, weight in zip(train, weights)
    )
    mu = weighted_goals / (2.0 * total_weight)
    if total_weight <= 0 or mu <= 0:
        raise ValueError("INVALID_FOLD_RECENCY_SCALE")
    model = fit_hierarchical_poisson(
        [_result(row) for row in train],
        as_of=cutoff,
        half_life_days=float(half_life),
        team_ridge=float(k) * mu / total_weight,
        competition_ridge=2.0 * float(k) * mu / total_weight,
        optimizer="newton",
        max_iterations=int(config["convergence"]["max_iterations"]),
        tolerance=float(config["convergence"]["gradient_norm_l2_max"]),
    )
    if not model.optimizer_converged:
        raise ArithmeticError("NEWTON_FIT_NOT_CONVERGED")
    climate = _climatology(train, cutoff)
    plain_rates = _plain_scaled_poisson(train, cutoff, half_life)
    model_rows, climate_rows, plain_rows = _score_rows(
        test, model, climate, plain_rates, blend_weight
    )
    return model, model_rows, climate_rows, plain_rows


def _detailed_metrics(
    model_rows: list[dict[str, Any]],
    climate_rows: list[dict[str, Any]],
    plain_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    diagnostics = evaluation_diagnostics(model_rows)
    return {
        "fixture_count": len(model_rows),
        "log_loss": _log_loss(model_rows),
        "multiclass_brier": _brier(model_rows),
        "vs_climatology": _comparison(model_rows, climate_rows),
        "vs_plain_scaled_poisson": _comparison(model_rows, plain_rows),
        "reliability_and_calibration": diagnostics["reliability"],
        "extreme_probability": diagnostics["extreme_probability"],
        "competition_breakdown": diagnostics["competition_breakdown"],
        "dispersion": _dispersion(model_rows),
    }


def _high_probability_gain_share(
    model_rows: list[dict[str, Any]], baseline_rows: list[dict[str, Any]], threshold: float
) -> dict[str, Any]:
    total_gain = 0.0
    high_gain = 0.0
    high_count = 0
    for model, baseline in zip(model_rows, baseline_rows):
        actual = _actual(model)
        gain = (
            -math.log(max(1e-15, baseline["probabilities"][actual]))
            + math.log(max(1e-15, model["probabilities"][actual]))
        )
        total_gain += gain
        high = any(float(model["probabilities"][outcome]) > threshold for outcome in OUTCOMES)
        if high:
            high_count += 1
            high_gain += gain
    return {
        "threshold": threshold,
        "high_probability_fixture_count": high_count,
        "total_log_loss_gain_vs_baseline": total_gain,
        "high_probability_log_loss_gain": high_gain,
        "share_of_total_gain_from_high_probability_fixtures": (
            high_gain / total_gain if abs(total_gain) > 1e-12 else None
        ),
    }


def _clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_json(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def run_evaluation(
    dataset_path: Path,
    config_path: Path,
    expected_config_sha: str,
    expected_dataset_sha: str,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    actual_config_sha = _sha256_config(config)
    if actual_config_sha != expected_config_sha:
        raise ValueError("FROZEN_CONFIG_SHA_MISMATCH")
    if config.get("schema_version") != "veltrix-shrinkage-selection-v3.2":
        raise ValueError("UNEXPECTED_PREREGISTRATION_VERSION")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows = dataset.get("training_only_rows")
    if not isinstance(rows, list) or len(rows) != 996:
        raise ValueError("EXPECTED_996_TRAINING_ROWS")
    if dataset.get("dataset_sha256") != expected_dataset_sha:
        raise ValueError("UNPINNED_DATASET_FINGERPRINT")

    folds = _folds(rows)
    development_folds = folds[:3]
    diagnostic_fold = folds[3]
    grid_records: list[dict[str, Any]] = []

    for fold in development_folds:
        train, test, cutoff = fold["train"], fold["test"], fold["cutoff"]
        for half_life in config["half_life_days_grid"]:
            for k in config["k_grid"]:
                fit_error = None
                model = None
                try:
                    weights = [_time_weight(row, cutoff, float(half_life)) for row in train]
                    total_weight = sum(weights)
                    mu = sum(
                        weight * (
                            int(row["label"]["home_goals"]) + int(row["label"]["away_goals"])
                        )
                        for row, weight in zip(train, weights)
                    ) / (2.0 * total_weight)
                    model = fit_hierarchical_poisson(
                        [_result(row) for row in train],
                        as_of=cutoff,
                        half_life_days=float(half_life),
                        team_ridge=float(k) * mu / total_weight,
                        competition_ridge=2.0 * float(k) * mu / total_weight,
                        optimizer="newton",
                        max_iterations=int(config["convergence"]["max_iterations"]),
                        tolerance=float(config["convergence"]["gradient_norm_l2_max"]),
                    )
                    if not model.optimizer_converged:
                        raise ArithmeticError("NEWTON_FIT_NOT_CONVERGED")
                except (ArithmeticError, ValueError, OverflowError, ZeroDivisionError) as exc:
                    fit_error = f"{type(exc).__name__}:{exc}"
                    model = None

                for blend_weight in config["blend_weight_grid"]:
                    base_record = {
                        "fold": fold["fold"],
                        "training_percent_start": FOLD_START_PERCENTAGES[fold["fold"] - 1],
                        "test_start_date": fold["test_start_date"],
                        "test_end_date": fold["test_end_date"],
                        "cutoff": cutoff.isoformat(),
                        "training_fixture_count": len(train),
                        "test_fixture_count": len(test),
                        "k": float(k),
                        "half_life_days": int(half_life),
                        "blend_weight": float(blend_weight),
                    }
                    if model is None:
                        grid_records.append({
                            **base_record,
                            "status": "INVALID_FIT_EXCLUDED",
                            "fit_converged": False,
                            "fit_failure": fit_error,
                        })
                        continue
                    climate = _climatology(train, cutoff)
                    plain_rates = _plain_scaled_poisson(train, cutoff, float(half_life))
                    model_rows, climate_rows, plain_rows = _score_rows(
                        test, model, climate, plain_rates, float(blend_weight)
                    )
                    grid_records.append({
                        **base_record,
                        "status": "SCORED",
                        "fit_converged": True,
                        "fit_iterations": model.optimizer_iterations,
                        "fit_gradient_norm": model.optimizer_gradient_norm,
                        "fit_relative_objective_change": model.optimizer_relative_objective_change,
                        "log_loss": _log_loss(model_rows),
                        "multiclass_brier": _brier(model_rows),
                        "vs_climatology": _comparison(model_rows, climate_rows),
                        "vs_plain_scaled_poisson": _comparison(model_rows, plain_rows),
                        "extreme_probability": evaluation_diagnostics(model_rows)["extreme_probability"],
                        "dispersion": _dispersion(model_rows),
                    })

    grouped: dict[tuple[float, int, float], list[dict[str, Any]]] = {}
    for record in grid_records:
        key = (record["k"], record["half_life_days"], record["blend_weight"])
        grouped.setdefault(key, []).append(record)
    ranking = []
    for key, records_for_key in grouped.items():
        records_for_key.sort(key=lambda item: item["fold"])
        if len(records_for_key) != 3 or any(item["status"] != "SCORED" for item in records_for_key):
            continue
        ranking.append({
            "k": key[0],
            "half_life_days": key[1],
            "blend_weight": key[2],
            "mean_fold_log_loss": sum(item["log_loss"] for item in records_for_key) / 3,
            "mean_fold_multiclass_brier": sum(item["multiclass_brier"] for item in records_for_key) / 3,
            "mean_fold_log_loss_difference_vs_climatology": (
                sum(item["vs_climatology"]["mean"] for item in records_for_key) / 3
            ),
            "mean_fold_log_loss_difference_vs_plain_scaled_poisson": (
                sum(item["vs_plain_scaled_poisson"]["mean"] for item in records_for_key) / 3
            ),
        })
    ranking.sort(key=lambda item: (
        item["mean_fold_log_loss"],
        item["mean_fold_multiclass_brier"],
        -item["k"],
        -item["half_life_days"],
        -item["blend_weight"],
    ))
    selected = ranking[0] if ranking else None

    selected_details = []
    fold4_replays = []
    if selected is not None:
        for fold in development_folds:
            model, model_rows, climate_rows, plain_rows = _fit_and_score(
                fold["train"], fold["test"], fold["cutoff"],
                selected["k"], selected["half_life_days"], selected["blend_weight"], config,
            )
            selected_details.append({
                "fold": fold["fold"],
                "test_start_date": fold["test_start_date"],
                "test_end_date": fold["test_end_date"],
                "cutoff": fold["cutoff"].isoformat(),
                "training_fixture_count": len(fold["train"]),
                "test_fixture_count": len(fold["test"]),
                "fit": {
                    "converged": model.optimizer_converged,
                    "iterations": model.optimizer_iterations,
                    "gradient_norm": model.optimizer_gradient_norm,
                    "relative_objective_change": model.optimizer_relative_objective_change,
                },
                "metrics": _detailed_metrics(model_rows, climate_rows, plain_rows),
            })

        for replay_name, replay_k in (
            ("SELECTED_CONFIGURATION", selected["k"]),
            ("K_0_5_AT_SELECTED_HALF_LIFE_AND_BLEND_WEIGHT", 0.5),
        ):
            model, model_rows, climate_rows, plain_rows = _fit_and_score(
                diagnostic_fold["train"], diagnostic_fold["test"], diagnostic_fold["cutoff"],
                replay_k, selected["half_life_days"], selected["blend_weight"], config,
            )
            detailed = _detailed_metrics(model_rows, climate_rows, plain_rows)
            detailed["high_probability_gain_attribution"] = {
                "vs_climatology": _high_probability_gain_share(
                    model_rows, climate_rows, float(config["calibration_admission"]["extreme_probability_threshold"])
                ),
                "vs_plain_scaled_poisson": _high_probability_gain_share(
                    model_rows, plain_rows, float(config["calibration_admission"]["extreme_probability_threshold"])
                ),
            }
            fold4_replays.append({
                "replay": replay_name,
                "k": replay_k,
                "half_life_days": selected["half_life_days"],
                "blend_weight": selected["blend_weight"],
                "test_start_date": diagnostic_fold["test_start_date"],
                "test_end_date": diagnostic_fold["test_end_date"],
                "cutoff": diagnostic_fold["cutoff"].isoformat(),
                "training_fixture_count": len(diagnostic_fold["train"]),
                "test_fixture_count": len(diagnostic_fold["test"]),
                "fit": {
                    "converged": model.optimizer_converged,
                    "iterations": model.optimizer_iterations,
                    "gradient_norm": model.optimizer_gradient_norm,
                    "relative_objective_change": model.optimizer_relative_objective_change,
                },
                "metrics": detailed,
            })

    dev_beats_climatology = bool(
        selected and selected["mean_fold_log_loss_difference_vs_climatology"] < 0
    )
    dev_beats_plain = bool(
        selected and selected["mean_fold_log_loss_difference_vs_plain_scaled_poisson"] < 0
    )
    fold4_sanity_pass = bool(
        len(fold4_replays) == 2
        and all(
            replay["metrics"]["vs_climatology"]["mean"] <= 0
            and replay["metrics"]["vs_plain_scaled_poisson"]["mean"] <= 0
            for replay in fold4_replays[:1]
        )
    )
    report = {
        "status": RETROSPECTIVE_STATUS,
        "certification": "RETROSPECTIVE_NOT_PIT_CERTIFIED",
        "historical_availability_rule": config["historical_availability_rule"],
        "config_sha256": actual_config_sha,
        "dataset_sha256": dataset["dataset_sha256"],
        "source_artifacts": {
            "dataset_run_id": 44873016040,
            "dataset_artifact_id": 14694463354,
            "forecast_run_id": 44873166128,
            "forecast_artifact_id": 14694089682,
            "forecast_count": 25,
            "forecast_dataset_sha256": dataset["dataset_sha256"],
        },
        "fold_definitions": [
            {
                "fold": fold["fold"],
                "training_start_date": fold["training_start_date"],
                "training_end_date": fold["training_end_date"],
                "test_start_date": fold["test_start_date"],
                "test_end_date": fold["test_end_date"],
                "cutoff": fold["cutoff"].isoformat(),
                "training_fixture_count": len(fold["train"]),
                "test_fixture_count": len(fold["test"]),
                "training_availability_rule": "kickoff_at_plus_3_hours_strictly_before_cutoff",
            }
            for fold in folds
        ],
        "development_grid_fold_metrics": grid_records,
        "selection_ranking": ranking,
        "selected_configuration": selected,
        "selected_configuration_detailed_metrics_folds_1_to_3": selected_details,
        "fold_4_replay_previously_examined_diagnostic_window": {
            "status": "PREVIOUSLY_EXAMINED_DIAGNOSTIC_WINDOW_SANITY_CHECK_ONLY",
            "limitation": "Not an untouched holdout; retrospective full-time proxy is not point-in-time certification.",
            "replays": fold4_replays,
        },
        "shadow_tier_gate": {
            "beats_climatology_on_development_folds_1_to_3": dev_beats_climatology,
            "beats_plain_scaled_poisson_on_development_folds_1_to_3": dev_beats_plain,
            "selected_configuration_does_not_lose_to_either_baseline_on_fold_4": fold4_sanity_pass,
            "automatic_admission": False,
            "maximum_permitted_tier": "SHADOW_RESEARCH_ONLY",
            "owner_review_required": True,
        },
        "invalid_fit_count": sum(1 for record in grid_records if record["status"] != "SCORED"),
        "fixture_level_rows_emitted": False,
        "team_names_or_scores_emitted": False,
        "database_writes": 0,
        "provider_calls": 0,
        "odds_calls": 0,
        "telegram_notifications": 0,
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
        "feed_state": "UNCHANGED",
    }
    return _clean_json(report)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: shrinkage_repair_evaluation.py DATASET_JSON CONFIG_JSON CONFIG_SHA256 DATASET_SHA256"
        )
    result = run_evaluation(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4])
    Path("shrinkage-retrospective-evaluation.json").write_text(
        json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
