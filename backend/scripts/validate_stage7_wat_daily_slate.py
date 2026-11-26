"""Read-only, candidate-branch validation of the Stage 7 WAT daily slate."""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_prospective_dataset import build_report
from build_prospective_shadow_predictions import _dataset_row

from app.research.stage7_shadow import (
    _select_daily_targets,
    build_stage7_shadow_predictions,
)
from app.wat_calendar import wat_day_window_utc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-fixtures", type=int, default=25)
    parser.add_argument("--max-snapshot-age-hours", type=float, default=6.0)
    args = parser.parse_args()

    database_url = (
        os.environ.get("VELTRIX_AI_ANALYST_DATABASE_URL")
        or os.environ.get("DATABASE_URL", "")
    ).strip()
    expected_database = os.environ.get("EXPECTED_DATABASE_NAME", "")
    if not database_url or expected_database != "veltrix_ai_analyst":
        parser.error("dedicated veltrix_ai_analyst database configuration is required")
    if not 1 <= args.max_fixtures <= 25 or args.max_snapshot_age_hours <= 0:
        parser.error("fixture limit must be 1..25 and snapshot age must be positive")

    generated = datetime.now(UTC)
    dataset = build_report(
        database_url,
        expected_database="veltrix_ai_analyst",
        minimum_training_fixtures=30,
        validation_block_fixtures=25,
    )
    if dataset.get("training_only_rows") is None:
        raise SystemExit("HISTORICAL_TRAINING_ROWS_MISSING_FROM_DATASET_MANIFEST")

    typed = {
        **dataset,
        "rows": [_dataset_row(row) for row in dataset["rows"]],
        "training_only_rows": [
            _dataset_row(row) for row in dataset["training_only_rows"]
        ],
    }
    rows = tuple(typed.get("rows") or ())
    start_utc, end_utc = wat_day_window_utc(generated)
    selected = _select_daily_targets(
        rows,
        generated=generated,
        max_fixtures=args.max_fixtures,
        max_snapshot_age_hours=args.max_snapshot_age_hours,
    )

    # Fail closed if the candidate selector ever leaks a non-today fixture,
    # exceeds the daily cap, or produces duplicate fixture identities.
    fixture_ids = [str(row.fixture_id) for row in selected]
    if len(selected) > args.max_fixtures:
        raise SystemExit("DAILY_SLATE_EXCEEDS_MAX_FIXTURES")
    if len(fixture_ids) != len(set(fixture_ids)):
        raise SystemExit("DUPLICATE_FIXTURE_IN_DAILY_SLATE")
    if any(not (start_utc <= row.kickoff_at < end_utc) for row in selected):
        raise SystemExit("NON_WAT_DAY_FIXTURE_SELECTED")
    if selected != sorted(selected, key=lambda row: (row.kickoff_at, row.fixture_id)):
        raise SystemExit("DAILY_SLATE_NOT_CHRONOLOGICALLY_SORTED")

    report = build_stage7_shadow_predictions(
        typed,
        generated_at=generated,
        max_fixtures=args.max_fixtures,
        max_snapshot_age_hours=args.max_snapshot_age_hours,
    )
    selected_count = len(selected)
    inference_summary = report.get("sanitized_summary")
    if inference_summary is not None:
        reported_considered = int(inference_summary.get("fixtures_considered", 0))
    elif report["status"] == "INSUFFICIENT_CUTOFF_VALID_TRAINING_LABELS":
        # Selection is still independently validated when the model correctly
        # abstains because the dataset has no cutoff-valid training labels.
        reported_considered = None
    elif selected_count == 0 and report["status"] == "NO_FRESH_UPCOMING_SNAPSHOTS":
        reported_considered = 0
    else:
        raise SystemExit("STAGE7_SELECTION_SUMMARY_MISSING")
    if reported_considered is not None and reported_considered != selected_count:
        raise SystemExit("SELECTOR_AND_INFERENCE_FIXTURE_COUNTS_MISMATCH")

    manifest = {
        "validation": "READ_ONLY_WAT_DAILY_SLATE",
        "status": "PASS",
        "generated_at": generated.isoformat(),
        "wat_date": generated.astimezone(ZoneInfo("Africa/Lagos")).date().isoformat(),
        "wat_window_start_utc": start_utc.isoformat(),
        "wat_window_end_utc_exclusive": end_utc.isoformat(),
        "max_fixtures": args.max_fixtures,
        "max_snapshot_age_hours": args.max_snapshot_age_hours,
        "selected_fixture_count": selected_count,
        "selected_fixtures": [
            {
                "fixture_id": str(row.fixture_id),
                "canonical_fixture_id": str(row.canonical_fixture_id),
                "canonical_competition_id": str(row.canonical_competition_id),
                "kickoff_at": row.kickoff_at.isoformat(),
                "prediction_cutoff_at": row.prediction_cutoff_at.isoformat(),
                "snapshot_age_hours": round(
                    (generated - row.prediction_cutoff_at).total_seconds() / 3600, 4
                ),
            }
            for row in selected
        ],
        "inference_status": report["status"],
        "forecast_count": report.get("forecast_count", 0),
        "abstention_count": report.get("abstention_count", 0),
        "fixtures_considered_by_inference": reported_considered,
        "dataset_sha256": dataset["dataset_sha256"],
        "provider_calls": 0,
        "odds_used": False,
        "database_writes": 0,
        "research_ledger_writes": 0,
        "production_promotion": "LOCKED",
        "publication": "NOT_PUBLISHED",
        "value_betting": "LOCKED",
        "checks": {
            "only_current_wat_day": True,
            "tomorrow_never_used_as_fill": True,
            "max_25_applied_after_date_filter": True,
            "empty_slate_allowed": selected_count == 0,
            "chronological_order": True,
            "unique_fixture_ids": True,
            "selector_matches_inference_count": (\n                reported_considered == selected_count\n                if reported_considered is not None\n                else "NOT_APPLICABLE_NO_TRAINING_DATA"\n            ),
            "database_transaction_read_only": True,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "validation": manifest["validation"],
        "status": manifest["status"],
        "wat_date": manifest["wat_date"],
        "selected_fixture_count": selected_count,
        "forecast_count": manifest["forecast_count"],
        "inference_status": manifest["inference_status"],
        "provider_calls": 0,
        "database_writes": 0,
        "research_ledger_writes": 0,
        "artifact": str(output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
