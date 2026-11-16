"""Fail-closed source rights and exact-scope evaluation.

This module is independent of provider transport and prediction logic. Every
ingestion or export path must evaluate a source approval before use.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ApprovalStatus(StrEnum):
    APPROVED = "APPROVED"
    PROVISIONAL = "PROVISIONAL"
    REVOKED = "REVOKED"


class DataUsePurpose(StrEnum):
    COLLECTION = "COLLECTION"
    STORAGE = "STORAGE"
    HISTORICAL_IMPORT = "HISTORICAL_IMPORT"
    INTERNAL_ANALYSIS = "INTERNAL_ANALYSIS"
    FEATURE_ENGINEERING = "FEATURE_ENGINEERING"
    MODEL_TRAINING = "MODEL_TRAINING"
    MODEL_VALIDATION = "MODEL_VALIDATION"
    BENCHMARKING = "BENCHMARKING"
    CACHE = "CACHE"
    PUBLIC_DISPLAY = "PUBLIC_DISPLAY"
    RAW_REDISTRIBUTION = "RAW_REDISTRIBUTION"


ALLOWED_RIGHTS_BASES = frozenset(
    {"TERMS", "WRITTEN_PERMISSION", "OPEN_LICENSE", "CONTRACT"}
)


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name}_MUST_BE_TIMEZONE_AWARE")


@dataclass(frozen=True, slots=True)
class SourceApproval:
    approval_id: str
    provider: str
    source_id: str
    scope_type: str
    scope_values: frozenset[str]
    data_types: frozenset[str]
    status: ApprovalStatus
    permitted_uses: frozenset[DataUsePurpose]
    commercial_use_allowed: bool
    terms_url: str | None
    terms_version: str | None
    evidence_uri: str | None
    evidence_sha256: str | None
    rights_basis: str | None
    reviewed_at_utc: datetime | None
    reviewer_id: str | None
    valid_from_utc: datetime
    valid_until_utc: datetime | None = None
    attribution_required: bool = False
    attribution_text: str | None = None
    attribution_url: str | None = None
    raw_redistribution_allowed: bool = False

    def __post_init__(self) -> None:
        required = (
            self.approval_id,
            self.provider,
            self.source_id,
            self.scope_type,
        )
        if any(not value or not value.strip() for value in required):
            raise ValueError("SOURCE_APPROVAL_IDENTITY_REQUIRED")
        if not self.scope_values or any(not value or not value.strip() for value in self.scope_values):
            raise ValueError("SOURCE_APPROVAL_EXACT_SCOPE_REQUIRED")
        if "*" in self.scope_values or "all" in {value.casefold() for value in self.scope_values}:
            raise ValueError("SOURCE_APPROVAL_WILDCARD_SCOPE_PROHIBITED")
        if not self.data_types or any(not value or not value.strip() for value in self.data_types):
            raise ValueError("SOURCE_APPROVAL_DATA_TYPE_REQUIRED")
        _require_aware(self.valid_from_utc, "VALID_FROM_UTC")
        if self.valid_until_utc is not None:
            _require_aware(self.valid_until_utc, "VALID_UNTIL_UTC")
            if self.valid_until_utc <= self.valid_from_utc:
                raise ValueError("SOURCE_APPROVAL_VALIDITY_EMPTY")
        if self.reviewed_at_utc is not None:
            _require_aware(self.reviewed_at_utc, "REVIEWED_AT_UTC")
        if self.status is ApprovalStatus.APPROVED:
            digest = self.evidence_sha256 or ""
            if not (
                self.permitted_uses
                and self.terms_url
                and self.terms_version
                and self.evidence_uri
                and self.reviewer_id
                and self.rights_basis in ALLOWED_RIGHTS_BASES
                and self.reviewed_at_utc is not None
                and len(digest) == 64
                and all(char in "0123456789abcdef" for char in digest.casefold())
            ):
                raise ValueError("APPROVED_SOURCE_REQUIRES_COMPLETE_RIGHTS_EVIDENCE")
            if self.attribution_required and not (
                self.attribution_text and self.attribution_url
            ):
                raise ValueError("APPROVED_SOURCE_ATTRIBUTION_INCOMPLETE")
            if (
                DataUsePurpose.RAW_REDISTRIBUTION in self.permitted_uses
                and not self.raw_redistribution_allowed
            ):
                raise ValueError("RAW_REDISTRIBUTION_PERMISSION_CONFLICT")


@dataclass(frozen=True, slots=True)
class RightsDecision:
    allowed: bool
    reason_code: str
    approval_id: str
    attribution_text: str | None = None
    attribution_url: str | None = None


def evaluate_source_use(
    approval: SourceApproval,
    purpose: DataUsePurpose,
    *,
    scope_value: str,
    at_utc: datetime,
    commercial: bool = False,
    public_facing: bool = False,
) -> RightsDecision:
    """Evaluate one requested use against one exact approved source scope."""
    _require_aware(at_utc, "RIGHTS_EVALUATION_TIME")
    evaluated_at = at_utc.astimezone(UTC)

    if approval.status is not ApprovalStatus.APPROVED:
        return RightsDecision(False, "SOURCE_RIGHTS_NOT_APPROVED", approval.approval_id)
    if scope_value not in approval.scope_values:
        return RightsDecision(False, "SOURCE_SCOPE_NOT_APPROVED", approval.approval_id)
    if evaluated_at < approval.valid_from_utc.astimezone(timezone.utc):
        return RightsDecision(False, "SOURCE_APPROVAL_NOT_YET_VALID", approval.approval_id)
    if (
        approval.valid_until_utc is not None
        and evaluated_at >= approval.valid_until_utc.astimezone(timezone.utc)
    ):
        return RightsDecision(False, "SOURCE_APPROVAL_EXPIRED", approval.approval_id)
    if purpose is DataUsePurpose.RAW_REDISTRIBUTION and not approval.raw_redistribution_allowed:
        return RightsDecision(False, "RAW_REDISTRIBUTION_PROHIBITED", approval.approval_id)
    if purpose not in approval.permitted_uses:
        return RightsDecision(False, "PURPOSE_NOT_PERMITTED", approval.approval_id)
    if commercial and not approval.commercial_use_allowed:
        return RightsDecision(False, "COMMERCIAL_USE_NOT_PERMITTED", approval.approval_id)
    if public_facing and approval.attribution_required:
        return RightsDecision(
            True,
            "APPROVED_WITH_ATTRIBUTION",
            approval.approval_id,
            approval.attribution_text,
            approval.attribution_url,
        )
    return RightsDecision(True, "APPROVED", approval.approval_id)


def evaluate_record_scope(
    approval: SourceApproval,
    *,
    provider: str,
    source_id: str,
    scope_type: str,
    scope_value: str,
    data_type: str,
    at_utc: datetime,
) -> RightsDecision:
    """Reject records whose provider, source, type, scope or approval validity fails."""
    _require_aware(at_utc, "RIGHTS_EVALUATION_TIME")
    evaluated_at = at_utc.astimezone(timezone.utc)
    if provider != approval.provider or source_id != approval.source_id:
        return RightsDecision(False, "SOURCE_APPROVAL_IDENTITY_MISMATCH", approval.approval_id)
    if scope_type != approval.scope_type or scope_value not in approval.scope_values:
        return RightsDecision(False, "SOURCE_SCOPE_NOT_APPROVED", approval.approval_id)
    if data_type not in approval.data_types:
        return RightsDecision(False, "SOURCE_DATA_TYPE_NOT_APPROVED", approval.approval_id)
    if approval.status is not ApprovalStatus.APPROVED:
        return RightsDecision(False, "SOURCE_RIGHTS_NOT_APPROVED", approval.approval_id)
    if evaluated_at < approval.valid_from_utc.astimezone(timezone.utc):
        return RightsDecision(False, "SOURCE_APPROVAL_NOT_YET_VALID", approval.approval_id)
    if (
        approval.valid_until_utc is not None
        and evaluated_at >= approval.valid_until_utc.astimezone(timezone.utc)
    ):
        return RightsDecision(False, "SOURCE_APPROVAL_EXPIRED", approval.approval_id)
    return RightsDecision(True, "SOURCE_RECORD_SCOPE_APPROVED", approval.approval_id)
