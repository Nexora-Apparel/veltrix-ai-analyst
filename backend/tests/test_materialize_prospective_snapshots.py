from __future__ import annotations

import pytest

from scripts.materialize_prospective_snapshots import validate_report


def valid_report():
    return {
        "report_type": "VELTRIX_PROSPECTIVE_EXPANDING_DATASET",
        "status": "READY_FOR_RESEARCH",
        "dataset_sha256": "a" * 64,
        "rows": [{
            "canonical_fixture_id": "00000000-0000-0000-0000-000000000001",
            "canonical_competition_id": "00000000-0000-0000-0000-000000000002",
            "home_team_id": "00000000-0000-0000-0000-000000000003",
            "away_team_id": "00000000-0000-0000-0000-000000000004",
            "provider_fixture_id": "fixture-1",
            "fixture_id": "league:fixture-1",
            "kickoff_at": "2026-01-02T12:00:00+00:00",
            "prediction_cutoff_at": "2026-01-02T10:00:00+00:00",
            "feature_lineage": [{
                "system_observed_at": "2026-01-02T09:00:00+00:00"
            }],
        }],
    }


def test_snapshot_report_requires_canonical_identity_and_strict_pit():
    assert len(validate_report(valid_report())) == 1


def test_snapshot_report_rejects_missing_canonical_identity():
    report = valid_report()
    report["rows"][0]["canonical_fixture_id"] = None
    with pytest.raises(ValueError, match="CANONICAL_SNAPSHOT_IDENTITY_MISSING"):
        validate_report(report)


def test_snapshot_report_rejects_feature_observed_at_kickoff():
    report = valid_report()
    report["rows"][0]["feature_lineage"][0]["system_observed_at"] = (
        report["rows"][0]["kickoff_at"]
    )
    with pytest.raises(ValueError, match="FEATURE_LINEAGE_NOT_STRICTLY_PRE_KICKOFF"):
        validate_report(report)


def test_snapshot_report_rejects_cutoff_at_kickoff():
    report = valid_report()
    report["rows"][0]["prediction_cutoff_at"] = report["rows"][0]["kickoff_at"]
    with pytest.raises(ValueError, match="PIT_CUTOFF_NOT_BEFORE_KICKOFF"):
        validate_report(report)
