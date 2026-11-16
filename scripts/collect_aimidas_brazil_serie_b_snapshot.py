"""Capture the approved pinned AI Midas Brazil Serie B snapshot locally."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.providers.aimidas_snapshot import collect_snapshot

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default=str(REPOSITORY_ROOT / ".local-data" / "aimidas" / "brazil-serie-b-2026"),
        help="Local private data directory; do not commit its contents.",
    )
    args = parser.parse_args()
    manifest = collect_snapshot(Path(args.output_dir))
    print(
        json.dumps(
            {
                "status": "SNAPSHOT_VERIFIED",
                "source_path": manifest["source_path"],
                "row_count": manifest["row_count"],
                "match_count": manifest["match_count"],
                "team_count": manifest["team_count"],
                "score_mismatch_row_count": manifest["score_mismatch_row_count"],
                "quarantined_match_count": manifest["quarantined_match_count"],
                "eligible_match_count": manifest["eligible_match_count"],
                "sha256": manifest["raw_file_sha256"],
                "point_in_time_certifiable": False,
                "model_admitted": False,
                "database_written": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
