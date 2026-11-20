"""Build research-only shadow forecasts from a read-only PIT dataset."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from app.research.prospective_shadow import build_shadow_predictions
from app.validation.prospective_dataset import ProspectiveDatasetRow
from build_prospective_dataset import build_report


def _datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _dataset_row(raw: dict) -> ProspectiveDatasetRow:
    return ProspectiveDatasetRow(
        fixture_id=str(raw["fixture_id"]),
        provider=str(raw["provider"]),
        source_id=str(raw["source_id"]),
        competition_id=str(raw["competition_id"]),
        kickoff_at=_datetime(raw["kickoff_at"]),
        prediction_cutoff_at=_datetime(raw.get("prediction_cutoff_at")),
        home_team_id=str(raw["home_team_id"]),
        away_team_id=str(raw["away_team_id"]),
        features=raw.get("features") or {},
        feature_lineage=tuple(raw.get("feature_lineage") or ()),
        label=raw.get("label"),
        label_observed_at=_datetime(raw.get("label_observed_at")),
        label_observation_id=raw.get("label_observation_id"),
        label_lineage=raw.get("label_lineage"),
        canonical_fixture_id=raw.get("canonical_fixture_id"),
        canonical_competition_id=raw.get("canonical_competition_id"),
        validation_eligible=raw.get("validation_eligible", True),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-fixtures", type=int, default=25)
    parser.add_argument("--max-snapshot-age-hours", type=float, default=6.0)
    parser.add_argument("--minimum-training-fixtures", type=int, default=30)
    parser.add_argument("--validation-block-fixtures", type=int, default=25)
    args = parser.parse_args()

    database_url = (
        os.getenv("VELTRIX_AI_ANALYST_DATABASE_URL")
        or os.getenv("DATABASE_URL", "")
    ).strip()
    expected_database = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not database_url or expected_database != "veltrix_ai_analyst":
        parser.error("dedicated veltrix_ai_analyst database configuration is required")
    if (
        args.max_fixtures < 1
        or args.max_snapshot_age_hours <= 0
        or args.minimum_training_fixtures < 1
        or args.validation_block_fixtures < 1
    ):
        parser.error("forecast and training limits must be positive")

    dataset = build_report(
        database_url,
        expected_database=expected_database,
        minimum_training_fixtures=args.minimum_training_fixtures,
        validation_block_fixtures=args.validation_block_fixtures,
    )
    if dataset.get("training_only_rows") is None:
        raise SystemExit("HISTORICAL_TRAINING_ROWS_MISSING_FROM_DATASET_MANIFEST")

    typed_dataset = {
        **dataset,
        "rows": [_dataset_row(row) for row in dataset["rows"]],
        "training_only_rows": [
            _dataset_row(row) for row in dataset["training_only_rows"]
        ],
    }
    report = build_shadow_predictions(
        typed_dataset,
        max_fixtures=args.max_fixtures,
        max_snapshot_age_hours=args.max_snapshot_age_hours,
        minimum_training_fixtures=args.minimum_training_fixtures,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": report["status"],
        "forecast_count": report.get("forecast_count", 0),
        "abstention_count": report.get("abstention_count", 0),
        "training_fixture_count": report.get("training_fixture_count", 0),
        "training_cutoff_at": report.get("training_cutoff_at"),
        "dataset_sha256": report.get("dataset_sha256"),
        "output": str(output),
        "provider_calls": 0,
        "database_writes": 0,
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
    }, sort_keys=True))
    if report["status"] != "SHADOW_FORECASTS_READY":
        raise SystemExit(report["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
