"""Build a PIT-only expanding-window report and score 1X2, BTTS and O/U."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from app.validation.prospective_dataset import ExpandingFold, ProspectiveDatasetRow
from app.validation.prospective_model_evaluation import evaluate_prospective_model
from scripts.build_prospective_dataset import build_report


def _datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _rows(values: list[dict]) -> tuple[ProspectiveDatasetRow, ...]:
    return tuple(
        ProspectiveDatasetRow(
            fixture_id=row["fixture_id"],
            provider=row["provider"],
            source_id=row["source_id"],
            competition_id=row["competition_id"],
            kickoff_at=_datetime(row["kickoff_at"]),
            prediction_cutoff_at=_datetime(row["prediction_cutoff_at"]),
            home_team_id=row["home_team_id"],
            away_team_id=row["away_team_id"],
            features=dict(row["features"]),
            feature_lineage=tuple(row["feature_lineage"]),
            label=dict(row["label"]) if row["label"] is not None else None,
            label_observed_at=_datetime(row["label_observed_at"]),
            label_observation_id=row["label_observation_id"],
            label_lineage=row["label_lineage"],
        )
        for row in values
    )


def _folds(values: list[dict]) -> tuple[ExpandingFold, ...]:
    return tuple(
        ExpandingFold(
            fold_number=int(row["fold_number"]),
            train_fixture_ids=tuple(row["train_fixture_ids"]),
            validation_fixture_ids=tuple(row["validation_fixture_ids"]),
            train_cutoff_at=_datetime(row["train_cutoff_at"]),
            validation_start_at=_datetime(row["validation_start_at"]),
            validation_end_at=_datetime(row["validation_end_at"]),
        )
        for row in values
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dataset-output")
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    args = parser.parse_args()
    database_url = (
        os.getenv("VELTRIX_AI_ANALYST_DATABASE_URL")
        or os.getenv("DATABASE_URL", "")
    ).strip()
    expected_database = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not database_url or expected_database != "veltrix_ai_analyst":
        parser.error("dedicated veltrix_ai_analyst database configuration is required")
    if args.bootstrap_replicates < 200:
        parser.error("bootstrap-replicates must be at least 200")

    dataset = build_report(
        database_url,
        expected_database=expected_database,
        minimum_training_fixtures=30,
        validation_block_fixtures=25,
    )
    evaluation = evaluate_prospective_model(
        _rows(dataset["rows"]),
        _folds(dataset["expanding_folds"]),
        bootstrap_replicates=args.bootstrap_replicates,
    )
    dataset_output = (
        Path(args.dataset_output)
        if args.dataset_output
        else Path(args.output).with_name("prospective-dataset.json")
    )
    dataset_output.parent.mkdir(parents=True, exist_ok=True)
    dataset_output.write_text(
        json.dumps(dataset, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    report = {
        **evaluation,
        "created_at": datetime.now(UTC).isoformat(),
        "source_dataset_sha256": dataset["dataset_sha256"],
        "source_dataset_status": dataset["status"],
        "fixture_identity_rows": dataset["fixture_identity_rows"],
        "eligible_prospective_rows": dataset["eligible_prospective_rows"],
        "settled_label_rows": dataset["settled_label_rows"],
        "distinct_competitions": dataset["distinct_competitions"],
        "distinct_kickoff_dates": dataset["distinct_kickoff_dates"],
        "feature_lineage_records": dataset["feature_lineage_records"],
        "feature_coverage": dataset["feature_coverage"],
        "model_feature_usage": "HIERARCHICAL_GOAL_RATE_ONLY; SHOT_POSSESSION_ATTACK_EVENT_FEATURES_CAPTURED_BUT_NOT_YET_USED",
        "invalid_system_observed_sightings": dataset["invalid_system_observed_sightings"],
        "source_data_provider": dataset["provider"],
        "point_in_time_policy": "SYSTEM_OBSERVED_AT_STRICTLY_BEFORE_TARGET_KICKOFF",
        "bookmaker_odds_used": False,
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
        "release_eligible": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": report["status"],
        "fixtures": report["fixtures"],
        "folds": len(report["folds"]),
        "source_dataset_sha256": report["source_dataset_sha256"],
        "output": str(output),
        "dataset_output": str(dataset_output),
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
