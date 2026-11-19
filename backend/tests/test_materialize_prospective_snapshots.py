from __future__ import annotations

import pytest

from scripts.materialize_prospective_snapshots import snapshot_digest, validate_report


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
                "system_observed_at": "2026-01-02T09:00:00+00:00",
                "retrieved_at": "2026-01-02T08:59:59+00:00",
                "availability_basis": "SYSTEM_OBSERVED_AT",
                "point_in_time_certifiable": True,
                "rights_approval_id": "approval-1",
                "rights_status": "APPROVED",
                "rights_permitted_uses": [
                    "FEATURE_ENGINEERING", "MODEL_TRAINING", "MODEL_VALIDATION"
                ],
                "payload_sha256": "b" * 64,
                "raw_response_sha256": "c" * 64,
                "source_observation_id": 1,
                "source_sighting_id": 2,
                "provider_response_id": 3,
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



def test_snapshot_digest_is_independent_of_later_outcome_label():
    row = valid_report()["rows"][0]
    original = snapshot_digest(row)
    row.update({
        "label": {"home_goals": 2, "away_goals": 1},
        "label_observed_at": "2026-01-02T14:00:00+00:00",
        "label_observation_id": 44,
        "label_lineage": {"source_observation_id": 44},
    })
    assert snapshot_digest(row) == original


def test_label_requires_post_kickoff_approved_pit_lineage():
    report = valid_report()
    row = report["rows"][0]
    row.update({
        "label": {"home_goals": 2, "away_goals": 1},
        "label_observed_at": "2026-01-02T14:00:00+00:00",
        "label_observation_id": 44,
        "label_lineage": {
            "availability_basis": "SYSTEM_OBSERVED_AT",
            "point_in_time_certifiable": True,
            "rights_status": "APPROVED",
            "rights_approval_id": "approval-1",
            "rights_permitted_uses": ["MODEL_TRAINING", "MODEL_VALIDATION"],
            "system_observed_at": "2026-01-02T14:00:00+00:00",
            "retrieved_at": "2026-01-02T13:59:59+00:00",
            "source_observation_id": 44,
            "source_sighting_id": 45,
            "provider_response_id": 46,
            "payload_sha256": "d" * 64,
            "raw_response_sha256": "e" * 64,
        },
    })
    assert len(validate_report(report)) == 1


def test_label_rejects_observation_at_kickoff():
    report = valid_report()
    row = report["rows"][0]
    row.update({
        "label": {"home_goals": 2, "away_goals": 1},
        "label_observed_at": row["kickoff_at"],
        "label_observation_id": 44,
        "label_lineage": {
            "availability_basis": "SYSTEM_OBSERVED_AT",
            "point_in_time_certifiable": True,
            "rights_status": "APPROVED",
            "rights_approval_id": "approval-1",
            "rights_permitted_uses": ["MODEL_TRAINING", "MODEL_VALIDATION"],
            "system_observed_at": row["kickoff_at"],
            "retrieved_at": "2026-01-02T11:59:59+00:00",
            "source_observation_id": 44,
            "source_sighting_id": 45,
            "provider_response_id": 46,
            "payload_sha256": "d" * 64,
            "raw_response_sha256": "e" * 64,
        },
    })
    with pytest.raises(ValueError, match="LABEL_LINEAGE_GATE_FAILED"):
        validate_report(report)
