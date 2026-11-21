from datetime import UTC, datetime, timedelta

from app.research.shrinkage_repair_evaluation import _folds


def _row(fixture_id: str, kickoff: datetime, observed_at: datetime) -> dict:
    return {
        "fixture_id": fixture_id,
        "canonical_competition_id": "league",
        "competition_id": "league",
        "canonical_fixture_id": fixture_id,
        "home_team_id": f"home-{fixture_id}",
        "away_team_id": f"away-{fixture_id}",
        "kickoff_at": kickoff.isoformat(),
        "label_observed_at": observed_at.isoformat(),
        "label": {"home_goals": 1, "away_goals": 0},
    }


def test_retrospective_availability_uses_kickoff_plus_three_hours_not_ingestion_time():
    start = datetime(2026, 1, 1, 12, tzinfo=UTC)
    bulk_ingestion = datetime(2026, 11, 16, 22, tzinfo=UTC)
    rows = [
        _row(f"day-{index}", start + timedelta(days=index), bulk_ingestion)
        for index in range(30)
    ]
    # The last result before the fold cutoff has not reached the three-hour
    # full-time proxy and must be excluded, despite its kickoff being earlier.
    near_cutoff = datetime(2026, 1, 18, 23, 30, tzinfo=UTC)
    rows.append(_row("late-prior-day", near_cutoff, bulk_ingestion))
    # Establish an early cutoff on the next day.
    early_test = datetime(2026, 1, 19, 0, 30, tzinfo=UTC)
    rows.append(_row("first-test", early_test, bulk_ingestion))

    folds = _folds(rows)
    fold_one = folds[0]
    cutoff = fold_one["cutoff"]
    training_ids = {row["fixture_id"] for row in fold_one["train"]}

    assert "late-prior-day" not in training_ids
    assert "day-0" in training_ids
    assert all(
        datetime.fromisoformat(row["kickoff_at"]) + timedelta(hours=3) < cutoff
        for row in fold_one["train"]
    )
    # Bulk ingestion timestamps are deliberately after the historical cutoff;
    # they must not be used to reject otherwise eligible historical outcomes.
    assert all(
        datetime.fromisoformat(row["label_observed_at"]) > cutoff
        for row in fold_one["train"]
    )


import hashlib
import json
import re
from pathlib import Path

from app.research.corrected_shrinkage_audit import _result


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_V32_CONFIG_SHA256 = "d087f3d641eccf8b81a6717d691db1edab0fd5402119182d18e01e56eadd176a"


def test_v32_canonical_config_hash_matches_workflow_and_preregistration():
    config_path = REPO_ROOT / "docs/research/shrinkage-selection-v3.json"
    workflow_path = REPO_ROOT / ".github/workflows/shrinkage-repair-evaluation.yml"
    preregistration_path = REPO_ROOT / "docs/research/shrinkage-selection-v3.2-preregistration.md"

    config = json.loads(config_path.read_text(encoding="utf-8"))
    canonical = json.dumps(
        config, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ) + "\\n"
    actual_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    workflow = workflow_path.read_text(encoding="utf-8")
    preregistration = preregistration_path.read_text(encoding="utf-8")

    default_match = re.search(
        r'config_sha256:\\s*\\n(?:[^\\n]*\\n)*?\\s+default:\\s*"([0-9a-f]{64})"',
        workflow,
    )
    hardcoded_match = re.search(
        r'\\[\\[ "\\$CONFIG_SHA256" == "([0-9a-f]{64})" \\]\\]',
        workflow,
    )
    preregistration_match = re.search(
        r"Canonical SHA-256: `([0-9a-f]{64})`", preregistration
    )

    assert config["schema_version"] == "veltrix-shrinkage-selection-v3.2"
    assert actual_hash == EXPECTED_V32_CONFIG_SHA256
    assert default_match and default_match.group(1) == actual_hash
    assert hardcoded_match and hardcoded_match.group(1) == actual_hash
    assert preregistration_match and preregistration_match.group(1) == actual_hash


def test_v32_preregistered_grid_is_exactly_120_configurations():
    config = json.loads(
        (REPO_ROOT / "docs/research/shrinkage-selection-v3.json").read_text(encoding="utf-8")
    )
    assert len(config["k_grid"]) == 10
    assert len(config["half_life_days_grid"]) == 3
    assert len(config["blend_weight_grid"]) == 4
    assert len(config["k_grid"]) * len(config["half_life_days_grid"]) * len(config["blend_weight_grid"]) == 120


def test_evaluator_accepts_pinned_dataset_training_row_field_contract():
    # Field names mirror the pinned prospective-dataset training_only_rows records.
    row = {
        "fixture_id": "field-contract-fixture",
        "competition_id": "competition-1",
        "home_team_id": "home-1",
        "away_team_id": "away-1",
        "kickoff_at": "2026-11-01T12:00:00+00:00",
        "label": {"home_goals": 2, "away_goals": 1},
    }
    result = _result(row)
    assert result.fixture_id == "field-contract-fixture"
    assert result.home_goals == 2
    assert result.away_goals == 1
