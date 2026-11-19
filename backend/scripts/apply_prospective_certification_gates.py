"""Apply strict production certification gates to research artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.validation.certification_gates import apply_prospective_certification_gates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", required=True)
    parser.add_argument("--dataset", required=True)
    args = parser.parse_args()

    evaluation_path = Path(args.evaluation)
    dataset_path = Path(args.dataset)
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(evaluation, dict) or not isinstance(dataset, dict):
        parser.error("evaluation and dataset artifacts must be JSON objects")

    report = apply_prospective_certification_gates(evaluation, dataset)
    evaluation_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    gates = report["certification_gates"]
    print(json.dumps({
        "status": report.get("status"),
        "fixtures_evaluated": report.get("fixtures", 0),
        "settled_labels": dataset.get("settled_label_rows", 0),
        "distinct_dates_with_settled_labels": dataset.get(
            "settled_distinct_kickoff_dates", 0
        ),
        "walk_forward_market_fixtures": gates[
            "walk_forward_fixtures_per_market"
        ]["observed"],
        "production_certification": report["production_certification"],
        "production_promotion": report["production_promotion"],
        "value_betting": report["value_betting"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
