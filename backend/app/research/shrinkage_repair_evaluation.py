from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models.hierarchical_poisson import fit_hierarchical_poisson
from app.research.corrected_shrinkage_audit import (
    _dt, _result,
)
from app.research.shrinkage_repair_metrics import (
    blend_probabilities, evaluation_diagnostics, paired_date_block_bootstrap,
)

OUTCOMES = ("HOME", "DRAW", "AWAY")


def _sha256_config(config: dict[str, Any]) -> str:
    canonical = json.dumps(
        config, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _poisson_rate_probabilities(home_rate: float, away_rate: float) -> dict[str, float]:
    home = [math.exp(-home_rate)]
    away = [math.exp(-away_rate)]
    for index in range(1, 13):
        home.append(home[-1] * home_rate / index)
        away.append(away[-1] * away_rate / index)
    h = d = a = 0.0
    for hi, hp in enumerate(home):
        for ai, ap in enumerate(away):
            if hi > ai:
                h += hp * ap
            elif hi == ai:
                d += hp * ap
            else:
                a += hp * ap
    total = h + d + a
    return {"HOME": h / total, "DRAW": d / total, "AWAY": a / total}


def _actual(row: dict[str, Any]) -> str:
    home, away = int(row["label"]["home_goals"]), int(row["label"]["away_goals"])
    return "HOME" if home > away else ("DRAW" if home == away else "AWAY")


def _log_loss(rows: list[dict[str, Any]]) -> float:
    return -sum(
        math.log(max(1e-15, row["probabilities"][_actual(row)])) for row in rows
    ) / len(rows)


def _brier(rows: list[dict[str, Any]]) -> float:
    return sum(
        sum(
            (row["probabilities"][outcome] - float(_actual(row) == outcome)) ** 2
            for outcome in OUTCOMES
        )
        for row in rows
    ) / len(rows)


def _climatology(train: list[dict[str, Any]], cutoff: datetime) -> dict[str, float]:
    import math as _math
    counts = dict.fromkeys(OUTCOMES, 0.0)
    weights = [
        _math.exp(-_math.log(2) * max(0.0, (cutoff - _dt(row["kickoff_at"])).total_seconds() / 86400) / 365.0)
        for row in train
    ]
    for row, weight in zip(train, weights):
        counts[_actual(row)] += weight
    total = sum(counts.values())
    return {outcome: counts[outcome] / total for outcome in OUTCOMES}


def _plain_scaled_poisson(train: list[dict[str, Any]], cutoff: datetime, half_life: float):
    weights = [
        math.exp(-math.log(2) * max(0.0, (cutoff - _dt(row["kickoff_at"])).total_seconds() / 86400) / half_life)
        for row in train
    ]
    total = sum(weights)
    home_rate = sum(w * int(r["label"]["home_goals"]) for r, w in zip(train, weights)) / total
    away_rate = sum(w * int(r["label"]["away_goals"]) for r, w in zip(train, weights)) / total
    return home_rate, away_rate


def _folds(rows: list[dict[str, Any]]):
    dates = sorted({_dt(row["kickoff_at"]).date().isoformat() for row in rows})
    for percent in (60, 70, 80):
        cut = max(1, min(len(dates) - 1, math.floor(len(dates) * percent / 100)))
        end = min(len(dates), cut + max(1, math.ceil(len(dates) * 0.10)))
        train_dates, test_dates = set(dates[:cut]), set(dates[cut:end])
        test = [r for r in rows if _dt(r["kickoff_at"]).date().isoformat() in test_dates]
        cutoff = min(_dt(r["kickoff_at"]) for r in test)
        # Enforce point-in-time label availability, not merely kickoff ordering.
        train = [
            r for r in rows
            if _dt(r["kickoff_at"]).date().isoformat() in train_dates
            and _dt(r["kickoff_at"]) < cutoff
            and r.get("label_observed_at") is not None
            and _dt(r["label_observed_at"]) < cutoff
        ]
        if not train or not test:
            raise ValueError(f"NO_POINT_IN_TIME_VALID_FOLD_DATA:{percent}")
        yield percent, train, test, cutoff


def _score_rows(test, model, climate, plain_rates, weight, competition_by_fixture):
    output = []
    for row in test:
        rates = model.predict(
            str(row["home_team_id"]), str(row["away_team_id"]), str(row["competition_id"])
        )
        raw = _poisson_rate_probabilities(rates.home_lambda, rates.away_lambda)
        probabilities = blend_probabilities(raw, climate, weight)
        plain = _poisson_rate_probabilities(*plain_rates)
        output.append({
            "competition_id": str(row["competition_id"]),
            "kickoff_at": row["kickoff_at"],
            "fixture_id": str(row["fixture_id"]),
            "label": row["label"],
            "probabilities": probabilities,
            "climatology_probabilities": climate,
            "plain_scaled_poisson_probabilities": plain,
        })
    return output


def run_evaluation(dataset_path: Path, config_path: Path, expected_config_sha: str, expected_dataset_sha: str) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    actual_sha = _sha256_config(config)
    if actual_sha != expected_config_sha:
        raise ValueError("FROZEN_CONFIG_SHA_MISMATCH")
    if config.get("schema_version") != "veltrix-shrinkage-selection-v3.1":
        raise ValueError("UNEXPECTED_PREREGISTRATION_VERSION")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows = dataset.get("training_only_rows")
    if not isinstance(rows, list) or len(rows) != 996:
        raise ValueError("EXPECTED_996_TRAINING_ROWS")
    if dataset.get("dataset_sha256") != expected_dataset_sha:
        raise ValueError("UNPINNED_DATASET_FINGERPRINT")

    fold_results = []
    candidate_records = []
    for fold_number, (percent, train, test, cutoff) in enumerate(_folds(rows), start=1):
        latest = cutoff
        climatology = _climatology(train, latest)
        fold_candidates = []
        for half_life in config["half_life_days_grid"]:
            weights = [
                math.exp(-math.log(2) * max(0.0, (latest - _dt(row["kickoff_at"])).total_seconds() / 86400) / half_life)
                for row in train
            ]
            total_weight = sum(weights)
            mu = sum(
                w * (int(row["label"]["home_goals"]) + int(row["label"]["away_goals"]))
                for row, w in zip(train, weights)
            ) / (2.0 * total_weight)
            plain_rates = _plain_scaled_poisson(train, latest, float(half_life))
            for k in config["k_grid"]:
                team_ridge = float(k) * mu / total_weight
                competition_ridge = 2.0 * float(k) * mu / total_weight
                fit_failure = None
                try:
                    model = fit_hierarchical_poisson(
                        [_result(row) for row in train],
                        as_of=latest,
                        half_life_days=float(half_life),
                        team_ridge=team_ridge,
                        competition_ridge=competition_ridge,
                        optimizer="newton",
                        max_iterations=int(config["convergence"]["max_iterations"]),
                        tolerance=float(config["convergence"]["gradient_norm_l2_max"]),
                    )
                except (ArithmeticError, ValueError, OverflowError) as exc:
                    model = None
                    fit_failure = f"{type(exc).__name__}:{exc}"
                for blend_weight in config["blend_weight_grid"]:
                    if model is None:
                        fold_candidates.append({
                            "fold": fold_number, "training_percent": percent,
                            "k": float(k), "half_life_days": int(half_life),
                            "blend_weight": float(blend_weight), "fit_converged": False,
                            "fit_failure": fit_failure, "status": "INVALID_FIT_EXCLUDED",
                        })
                        continue
                    scored = _score_rows(test, model, climatology, plain_rates, float(blend_weight), {})
                    model_rows = [{"competition_id":r["competition_id"],"kickoff_at":r["kickoff_at"],"label":r["label"],"probabilities":r["probabilities"]} for r in scored]
                    climate_rows = [{"competition_id":r["competition_id"],"kickoff_at":r["kickoff_at"],"label":r["label"],"probabilities":r["climatology_probabilities"]} for r in scored]
                    plain_rows = [{"competition_id":r["competition_id"],"kickoff_at":r["kickoff_at"],"label":r["label"],"probabilities":r["plain_scaled_poisson_probabilities"]} for r in scored]
                    differences = {}
                    for baseline_name, baseline_rows in (("climatology", climate_rows), ("plain_scaled_poisson", plain_rows)):
                        paired = []
                        for model_row, base_row in zip(model_rows, baseline_rows):
                            actual = _actual(model_row)
                            delta = -math.log(max(1e-15, model_row["probabilities"][actual])) + math.log(max(1e-15, base_row["probabilities"][actual]))
                            paired.append((_dt(model_row["kickoff_at"]).date().isoformat(), delta))
                        differences[baseline_name] = paired_date_block_bootstrap(paired)
                    metrics = evaluation_diagnostics(model_rows)
                    record = {
                        "fold": fold_number, "training_percent": percent,
                        "test_rows": len(test),
                        "k": float(k), "half_life_days": int(half_life),
                        "blend_weight": float(blend_weight),
                        "log_loss": metrics["log_loss"],
                        "multiclass_brier": metrics["multiclass_brier"],
                        "vs_climatology": differences["climatology"],
                        "vs_plain_scaled_poisson": differences["plain_scaled_poisson"],
                        "calibration": metrics["reliability"],
                        "extreme_probability": metrics["extreme_probability"],
                        "competition_breakdown": metrics["competition_breakdown"],
                        "fit_converged": model.optimizer_converged,
                        "fit_iterations": model.optimizer_iterations,
                        "fit_gradient_norm": model.optimizer_gradient_norm,
                        "fit_relative_objective_change": model.optimizer_relative_objective_change,
                    }
                    fold_candidates.append(record)
                    candidate_records.append(record)
        fold_results.append({"fold":fold_number,"train_rows":len(train),"test_rows":len(test),"cutoff":cutoff.isoformat(),"candidates":fold_candidates})

    # Pooled development loss; deterministic tie-break: lower pooled Brier,
    # then larger k (stronger shrinkage), longer half-life, then larger blend w.
    grouped = {}
    for record in candidate_records:
        key = (record["k"], record["half_life_days"], record["blend_weight"])
        grouped.setdefault(key, []).append(record)
    selection = []
    for key, records_for_key in grouped.items():
        if len(records_for_key) != 3 or any(not item.get("fit_converged") for item in records_for_key):
            continue
        loss = sum(item["log_loss"] for item in records_for_key) / 3
        brier = sum(item["multiclass_brier"] for item in records_for_key) / 3
        selection.append({"k":key[0],"half_life_days":key[1],"blend_weight":key[2],"mean_fold_log_loss":loss,"mean_fold_brier":brier})
    selection.sort(key=lambda x:(x["mean_fold_log_loss"],x["mean_fold_brier"],-x["k"],-x["half_life_days"],-x["blend_weight"]))
    return {
        "status":"DEVELOPMENT_EVALUATION_COMPLETE",
        "config_sha256":actual_sha,
        "dataset_sha256":dataset["dataset_sha256"],
        "folds":fold_results,
        "selection_ranking":selection,
        "selected_config":selection[0] if selection else None,
        "selection_rule":config["selection_rule"],
        "invalid_fit_count":sum(1 for fold in fold_results for item in fold["candidates"] if not item.get("fit_converged")),
        "fold_4_status":"NOT_RUN_BY_DEVELOPMENT_SELECTOR; PREVIOUSLY_EXAMINED_DIAGNOSTIC_WINDOW REQUIRES SEPARATE LEAKAGE-CLEARED SANITY CHECK",
        "admission":"NOT_ADMITTED_PENDING_PREVIOUSLY_EXAMINED_WINDOW_AND_OWNER_REVIEW",
        "production_promotion":"LOCKED",
        "value_betting":"LOCKED",
    }


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: evaluate_shrinkage_repair.py DATASET_JSON CONFIG_JSON CONFIG_SHA256 DATASET_SHA256")
    report = run_evaluation(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4])
    Path("shrinkage-development-report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
