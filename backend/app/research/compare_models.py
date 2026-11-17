"""Matched fixed-v1 versus nested-v2 chronological research comparison."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace

from app.research.retrospective_run import load_completed_results
from app.validation.bootstrap import paired_fold_block_bootstrap
from app.validation.retrospective import evaluate_retrospective


def compare_models(results):
    """Score both candidates on identical outer fixtures and chronological folds."""
    fixed = evaluate_retrospective(results, nested_tuning=False)
    nested = evaluate_retrospective(results, nested_tuning=True)
    fixed_rows = {row.fixture_id: row for row in fixed.predictions}
    nested_rows = {row.fixture_id: row for row in nested.predictions}
    if fixed_rows.keys() != nested_rows.keys():
        raise RuntimeError("MODEL_COMPARISON_OUTER_FIXTURE_MISMATCH")
    if any(fixed_rows[key].fold_index != nested_rows[key].fold_index for key in fixed_rows):
        raise RuntimeError("MODEL_COMPARISON_OUTER_FOLD_MISMATCH")

    paired_folds = []
    fold_output = []
    for fixed_fold, nested_fold in zip(fixed.fold_metrics, nested.fold_metrics):
        if fixed_fold.fold_index != nested_fold.fold_index:
            raise RuntimeError("MODEL_COMPARISON_FOLD_ORDER_MISMATCH")
        paired_folds.append(SimpleNamespace(
            fixture_count=fixed_fold.fixture_count,
            brier_1x2=nested_fold.brier_1x2,
            baseline_brier_1x2=fixed_fold.brier_1x2,
            log_loss_1x2=nested_fold.log_loss_1x2,
            baseline_log_loss_1x2=fixed_fold.log_loss_1x2,
        ))
        fold_output.append({
            "fold_index": fixed_fold.fold_index,
            "fixture_count": fixed_fold.fixture_count,
            "test_start_at": fixed_fold.test_start_at.isoformat(),
            "test_end_at": fixed_fold.test_end_at.isoformat(),
            "fixed_v1_brier": fixed_fold.brier_1x2,
            "nested_v2_brier": nested_fold.brier_1x2,
            "brier_difference_v2_minus_v1": nested_fold.brier_1x2 - fixed_fold.brier_1x2,
            "fixed_v1_log_loss": fixed_fold.log_loss_1x2,
            "nested_v2_log_loss": nested_fold.log_loss_1x2,
            "log_loss_difference_v2_minus_v1": nested_fold.log_loss_1x2 - fixed_fold.log_loss_1x2,
            "v2_half_life_days": nested_fold.half_life_days,
            "v2_ridge": nested_fold.ridge,
            "v2_rho": nested_fold.rho,
        })

    bootstrap = paired_fold_block_bootstrap(paired_folds)
    return {
        "evaluation_type": "MATCHED_RETROSPECTIVE_EVENT_TIME_NOT_PIT_CERTIFIED",
        "fixed_v1": {
            "evaluated_fixtures": fixed.evaluated_fixtures,
            "fold_count": fixed.fold_count,
            "brier_1x2": fixed.brier_1x2,
            "log_loss_1x2": fixed.log_loss_1x2,
            "classwise_ece": fixed.classwise_ece,
            "top_label_ece": fixed.top_label_ece,
        },
        "nested_v2": {
            "evaluated_fixtures": nested.evaluated_fixtures,
            "fold_count": nested.fold_count,
            "brier_1x2": nested.brier_1x2,
            "log_loss_1x2": nested.log_loss_1x2,
            "classwise_ece": nested.classwise_ece,
            "top_label_ece": nested.top_label_ece,
        },
        "paired_differences": {
            "convention": "NESTED_V2_MINUS_FIXED_V1; NEGATIVE_FAVOURS_V2",
            "brier": {
                "mean": bootstrap.brier_difference.mean_difference,
                "lower_95": bootstrap.brier_difference.lower_95,
                "upper_95": bootstrap.brier_difference.upper_95,
            },
            "log_loss": {
                "mean": bootstrap.log_loss_difference.mean_difference,
                "lower_95": bootstrap.log_loss_difference.lower_95,
                "upper_95": bootstrap.log_loss_difference.upper_95,
            },
            "resamples": bootstrap.resamples,
            "seed": bootstrap.seed,
            "interpretation": "EXPLORATORY_FOLD_BLOCK_BOOTSTRAP_ONLY_12_FOLDS",
        },
        "folds": fold_output,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/matched-v1-v2.json"))
    args = parser.parse_args()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is required")
    report = compare_models(load_completed_results(dsn))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("evaluation_type", "fixed_v1", "nested_v2", "paired_differences")}, indent=2))


if __name__ == "__main__":
    main()
