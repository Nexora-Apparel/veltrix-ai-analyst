from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.providers.rights import (
    ApprovalStatus,
    DataUsePurpose,
    SourceApproval,
    evaluate_record_scope,
    evaluate_source_use,
)


def approved_source() -> SourceApproval:
    return SourceApproval(
        approval_id="approval-test-001",
        provider="test-provider",
        source_id="test-source",
        scope_type="competition_id",
        scope_values=frozenset({"league-1", "league-2"}),
        data_types=frozenset({"fixtures_and_results"}),
        status=ApprovalStatus.APPROVED,
        permitted_uses=frozenset(
            {
                DataUsePurpose.COLLECTION,
                DataUsePurpose.STORAGE,
                DataUsePurpose.HISTORICAL_IMPORT,
                DataUsePurpose.INTERNAL_ANALYSIS,
                DataUsePurpose.PUBLIC_DISPLAY,
            }
        ),
        commercial_use_allowed=False,
        terms_url="https://example.test/terms",
        terms_version="2026-11",
        evidence_uri="https://example.test/approval",
        evidence_sha256="a" * 64,
        rights_basis="WRITTEN_PERMISSION",
        reviewed_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        reviewer_id="project-owner",
        valid_from_utc=datetime(2026, 11, 1, tzinfo=UTC),
        valid_until_utc=datetime(2027, 1, 1, tzinfo=UTC),
        attribution_required=True,
        attribution_text="Example Data",
        attribution_url="https://example.test",
        raw_redistribution_allowed=False,
    )


def test_approved_internal_collection_is_allowed() -> None:
    decision = evaluate_source_use(
        approved_source(),
        DataUsePurpose.COLLECTION,
        scope_value="league-1",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
    )

    assert decision.allowed is True
    assert decision.reason_code == "APPROVED"


def test_public_display_returns_required_attribution() -> None:
    decision = evaluate_source_use(
        approved_source(),
        DataUsePurpose.PUBLIC_DISPLAY,
        scope_value="league-1",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
        public_facing=True,
    )

    assert decision.allowed is True
    assert decision.reason_code == "APPROVED_WITH_ATTRIBUTION"
    assert decision.attribution_text == "Example Data"
    assert decision.attribution_url == "https://example.test"


def test_out_of_scope_competition_is_denied() -> None:
    decision = evaluate_source_use(
        approved_source(),
        DataUsePurpose.COLLECTION,
        scope_value="unapproved-league",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
    )

    assert decision.allowed is False
    assert decision.reason_code == "SOURCE_SCOPE_NOT_APPROVED"


def test_commercial_use_is_denied_by_noncommercial_approval() -> None:
    decision = evaluate_source_use(
        approved_source(),
        DataUsePurpose.INTERNAL_ANALYSIS,
        scope_value="league-1",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
        commercial=True,
    )

    assert decision.allowed is False
    assert decision.reason_code == "COMMERCIAL_USE_NOT_PERMITTED"


def test_raw_redistribution_is_denied() -> None:
    decision = evaluate_source_use(
        approved_source(),
        DataUsePurpose.RAW_REDISTRIBUTION,
        scope_value="league-1",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
    )

    assert decision.allowed is False
    assert decision.reason_code == "RAW_REDISTRIBUTION_PROHIBITED"


def test_expired_approval_is_denied() -> None:
    decision = evaluate_source_use(
        approved_source(),
        DataUsePurpose.COLLECTION,
        scope_value="league-1",
        at_utc=datetime(2027, 1, 1, tzinfo=UTC),
    )

    assert decision.allowed is False
    assert decision.reason_code == "SOURCE_APPROVAL_EXPIRED"


def test_provisional_approval_is_denied() -> None:
    provisional = replace(approved_source(), status=ApprovalStatus.PROVISIONAL)
    decision = evaluate_source_use(
        provisional,
        DataUsePurpose.COLLECTION,
        scope_value="league-1",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
    )

    assert decision.allowed is False
    assert decision.reason_code == "SOURCE_RIGHTS_NOT_APPROVED"


def test_approved_source_requires_complete_evidence() -> None:
    with pytest.raises(ValueError, match="APPROVED_SOURCE_REQUIRES_COMPLETE_RIGHTS_EVIDENCE"):
        replace(approved_source(), evidence_sha256=None)


def test_wildcard_scope_is_rejected() -> None:
    with pytest.raises(ValueError, match="SOURCE_APPROVAL_WILDCARD_SCOPE_PROHIBITED"):
        replace(approved_source(), scope_values=frozenset({"*"}))


def test_record_scope_checks_provider_source_and_data_type() -> None:
    decision = evaluate_record_scope(
        approved_source(),
        provider="test-provider",
        source_id="test-source",
        scope_type="competition_id",
        scope_value="league-1",
        data_type="fixtures_and_results",
    )

    assert decision.allowed is True
    wrong_source = evaluate_record_scope(
        approved_source(),
        provider="other-provider",
        source_id="test-source",
        scope_type="competition_id",
        scope_value="league-1",
        data_type="fixtures_and_results",
    )
    assert wrong_source.reason_code == "SOURCE_APPROVAL_IDENTITY_MISMATCH"


def test_rights_evaluation_requires_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="RIGHTS_EVALUATION_TIME_MUST_BE_TIMEZONE_AWARE"):
        evaluate_source_use(
            approved_source(),
            DataUsePurpose.COLLECTION,
            scope_value="league-1",
            at_utc=datetime(2026, 11, 16),
        )
