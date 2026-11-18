"""Generate paired diagnostics from an existing retrospective prequential report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.validation.paired_chronological import evaluate_paired_chronological_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resamples", type=int, default=2000)
    parser.add_argument("--block-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261118)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    diagnostics = evaluate_paired_chronological_report(
        report,
        resamples=args.resamples,
        block_size=args.block_size,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True, allow_nan=False) + "\\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "PAIRED_CHRONOLOGICAL_DIAGNOSTICS_COMPLETE",
        "fixture_count": diagnostics["fixture_count"],
        "output": str(args.output),
        "protocol": diagnostics["evaluation_type"],
        "source_report_sha256": diagnostics["source_report_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
