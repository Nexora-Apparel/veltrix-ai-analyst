"""Explicitly persist a research-only shadow report to the isolated ledger."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.research.shadow_ledger import persist_shadow_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--code-commit", default=os.getenv("GITHUB_SHA", ""))
    parser.add_argument("--confirm-research-ledger-write", action="store_true")
    args = parser.parse_args()

    enabled = (
        args.confirm_research_ledger_write
        and os.getenv("VELTRIX_SHADOW_LEDGER_WRITE_ENABLED") == "true"
    )
    if not enabled:
        parser.error(
            "writing requires --confirm-research-ledger-write and "
            "VELTRIX_SHADOW_LEDGER_WRITE_ENABLED=true"
        )
    database_url = os.getenv("VELTRIX_SHADOW_LEDGER_DATABASE_URL", "").strip()
    if not database_url:
        parser.error("VELTRIX_SHADOW_LEDGER_DATABASE_URL is required")
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    result = persist_shadow_report(
        database_url,
        report,
        code_commit=args.code_commit,
        write_enabled=True,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
