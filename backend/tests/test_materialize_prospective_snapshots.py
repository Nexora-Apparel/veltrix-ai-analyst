from __future__ import annotations

import hashlib

import pytest

from scripts.materialize_prospective_snapshots import (
    canonical_json,
    resolve_existing_snapshot,
    snapshot_conflict_context,
    snapshot_digest,
    validate_report,
)


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
            "features": {"home_matches_last5": 3.0},
            "kickoff_at": "2026-01-02T12:00:00+00:00",
            "prediction_cutoff_at": "2026-01-02T10:00:00+00:00",
            "feature_lineage": [{
                "system_observed_at": "2026-01-02T09:00:00+00:00",
                "retrieved_at": "2026-01-02T08:59:59+00:00",
                "availability_basis": "SYSTEM_OBSERVED_AT",
                "point_in_time_certifiable": True,
                "rights_approval_id": "approval-1",
                "rights_valid_from": "2025-12-01T00:00:00+00:00",
                "rights_valid_until": None,
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
            "rights_valid_from": "2025-12-01T00:00:00+00:00",
            "rights_valid_until": None,
            "rights_status_events": [],
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



def test_feature_lineage_rejects_rights_revoked_before_observation():
    report = valid_report()
    report["rows"][0]["feature_lineage"][0]["rights_status_events"] = [{
        "id": 1,
        "status": "REVOKED",
        "effective_at": "2026-01-02T08:30:00+00:00",
    }]
    with pytest.raises(
        ValueError, match="FEATURE_LINEAGE_RIGHTS_OR_PIT_GATE_FAILED"
    ):
        validate_report(report)



def test_snapshot_digest_preserves_existing_null_label_hash():
    row = valid_report()["rows"][0]
    legacy_row = {
        **row,
        "label": None,
        "label_observed_at": None,
        "label_observation_id": None,
        "label_lineage": None,
    }
    expected = hashlib.sha256(canonical_json(legacy_row).encode("utf-8")).hexdigest()
    assert snapshot_digest(row) == expected


def test_snapshot_conflict_context_identifies_key_and_payload_differences():
    row = valid_report()["rows"][0]
    existing_features = {"home_matches_last5": 4.0}
    existing_lineage = [{"source_observation_id": 10}]
    context = snapshot_conflict_context(
        row,
        existing_id=99,
        existing_digest="f" * 64,
        existing_features=existing_features,
        existing_lineage=existing_lineage,
    )
    assert context["canonical_fixture_id"] == row["canonical_fixture_id"]
    assert context["provider_fixture_id"] == row["provider_fixture_id"]
    assert context["prediction_cutoff_at"] == row["prediction_cutoff_at"]
    assert context["feature_schema_version"] == "veltrix-pit-features-v1"
    assert context["existing_snapshot_id"] == 99
    assert context["existing_snapshot_sha256"] == "f" * 64
    assert context["proposed_snapshot_sha256"] == snapshot_digest(row)
    assert context["feature_payloads_differ"] is True
    assert context["feature_lineage_payloads_differ"] is True
    assert "features" not in context
    assert "feature_lineage" not in context


def test_snapshot_conflict_context_reports_matching_payloads():
    row = valid_report()["rows"][0]
    context = snapshot_conflict_context(
        row,
        existing_id=99,
        existing_digest=snapshot_digest(row),
        existing_features=row["features"],
        existing_lineage=row["feature_lineage"],
    )
    assert context["feature_payloads_differ"] is False
    assert context["feature_lineage_payloads_differ"] is False


def test_same_key_and_same_digest_is_an_idempotent_replay():
    row = valid_report()["rows"][0]
    snapshot_id = resolve_existing_snapshot(
        row,
        (123, snapshot_digest(row), row["features"], row["feature_lineage"]),
    )
    assert snapshot_id == 123


def test_same_key_and_different_digest_fails_closed_without_mutating_existing_payload():
    row = valid_report()["rows"][0]
    existing_features = {"home_matches_last5": 4.0}
    existing_lineage = [{"source_observation_id": 10}]
    original_features = dict(existing_features)
    original_lineage = list(existing_lineage)
    with pytest.raises(RuntimeError, match="IMMUTABLE_SNAPSHOT_IDEMPOTENCY_CONFLICT"):
        resolve_existing_snapshot(
            row,
            (123, "f" * 64, existing_features, existing_lineage),
        )
    assert existing_features == original_features
    assert existing_lineage == original_lineage
