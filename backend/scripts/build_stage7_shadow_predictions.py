"""Build selected Stage 7 Newton shadow forecasts from cutoff-valid snapshots."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from build_prospective_dataset import build_report
from build_prospective_shadow_predictions import _dataset_row

from app.research.stage7_shadow import build_run_summary, build_stage7_shadow_predictions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-fixtures", type=int, default=25)
    parser.add_argument("--max-snapshot-age-hours", type=float, default=6.0)
    args = parser.parse_args()
    database_url = (
        os.getenv("VELTRIX_AI_ANALYST_DATABASE_URL")
        or os.getenv("DATABASE_URL", "")
    ).strip()
    if not database_url or os.getenv("EXPECTED_DATABASE_NAME") != "veltrix_ai_analyst":
        parser.error("dedicated veltrix_ai_analyst database configuration is required")
    if args.max_fixtures < 1 or args.max_fixtures > 25 or args.max_snapshot_age_hours <= 0:
        parser.error("fixture limit must be 1..25 and snapshot age must be positive")

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
    report = build_stage7_shadow_predictions(
        typed,
        max_fixtures=args.max_fixtures,
        max_snapshot_age_hours=args.max_snapshot_age_hours,
    )
    if report["predictions"]:
        team_ids = sorted({
            team_id
            for prediction in report["predictions"]
            for team_id in (
                prediction["home_canonical_team_id"],
                prediction["away_canonical_team_id"],
            )
        })
        competition_ids = sorted({
            prediction["canonical_competition_id"]
            for prediction in report["predictions"]
        })
        with psycopg.connect(database_url, row_factory=dict_row) as connection:
            if connection.info.dbname != "veltrix_ai_analyst":
                raise RuntimeError("DATABASE_NAME_MISMATCH")
            teams = connection.execute(
                """SELECT id::text AS id, display_name
                   FROM veltrix_ai_analyst.canonical_teams
                   WHERE id::text = ANY(%s)""",
                (team_ids,),
            ).fetchall()
            competitions = connection.execute(
                """SELECT id::text AS id, display_name
                   FROM veltrix_ai_analyst.canonical_competitions
                   WHERE id::text = ANY(%s)""",
                (competition_ids,),
            ).fetchall()
        team_names = {row["id"]: row["display_name"] for row in teams}
        competition_names = {row["id"]: row["display_name"] for row in competitions}
        for prediction in report["predictions"]:
            prediction["home_team"] = team_names.get(
                prediction["home_canonical_team_id"], "UNRESOLVED_TEAM"
            )
            prediction["away_team"] = team_names.get(
                prediction["away_canonical_team_id"], "UNRESOLVED_TEAM"
            )
            prediction["competition"] = competition_names.get(
                prediction["canonical_competition_id"], "UNRESOLVED_COMPETITION"
            )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    summary = build_run_summary(report)
    summary_path = output.with_name("stage7-shadow-sanitized-summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
