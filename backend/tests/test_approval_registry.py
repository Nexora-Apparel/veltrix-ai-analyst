from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from app.providers.approvals import (
    AIMIDAS_BRAZIL_SERIE_B_APPROVAL,
    FIVEDOLLAR_ACCOUNT_APPROVAL,
    FIVEDOLLAR_COMMUNITY_APPROVAL,
    THE_ODDS_API_SOCCER_APPROVAL,
)
from app.providers.rights import DataUsePurpose, evaluate_source_use


def test_5dollar_approval_is_limited_to_seven_verified_competitions() -> None:
    approval = FIVEDOLLAR_COMMUNITY_APPROVAL

    assert len(approval.scope_values) == 7
    assert "522514093" in approval.scope_values
    assert "*" not in approval.scope_values
    assert approval.commercial_use_allowed is False
    assert approval.raw_redistribution_allowed is False

    allowed = evaluate_source_use(
        approval,
        DataUsePurpose.HISTORICAL_IMPORT,
        scope_value="522514093",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
    )
    denied = evaluate_source_use(
        approval,
        DataUsePurpose.HISTORICAL_IMPORT,
        scope_value="unverified-league",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
    )

    assert allowed.allowed is True
    assert denied.allowed is False


def test_5dollar_public_display_requires_attribution() -> None:
    decision = evaluate_source_use(
        FIVEDOLLAR_COMMUNITY_APPROVAL,
        DataUsePurpose.PUBLIC_DISPLAY,
        scope_value="522514093",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
        public_facing=True,
    )

    assert decision.allowed is True
    assert decision.reason_code == "APPROVED_WITH_ATTRIBUTION"
    assert decision.attribution_text == "Football data by 5DollarFootballAPI"


def test_ai_midas_approval_is_file_specific_and_noncommercial() -> None:
    approval = AIMIDAS_BRAZIL_SERIE_B_APPROVAL

    assert approval.scope_values == frozenset({"advanced stats/Brazil Serie B 2026.csv"})
    assert approval.commercial_use_allowed is False
    assert approval.raw_redistribution_allowed is False

    allowed = evaluate_source_use(
        approval,
        DataUsePurpose.INTERNAL_ANALYSIS,
        scope_value="advanced stats/Brazil Serie B 2026.csv",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
    )
    raw_export = evaluate_source_use(
        approval,
        DataUsePurpose.RAW_REDISTRIBUTION,
        scope_value="advanced stats/Brazil Serie B 2026.csv",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
    )

    assert allowed.allowed is True
    assert raw_export.allowed is False



def test_5dollar_approval_evidence_hash_matches_committed_review() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    evidence = repository_root / "docs" / "providers" / "5DOLLAR_TERMS_REVIEW.md"

    assert sha256(evidence.read_bytes()).hexdigest() == FIVEDOLLAR_COMMUNITY_APPROVAL.evidence_sha256



def test_5dollar_account_approval_is_limited_to_account_metadata() -> None:
    approval = FIVEDOLLAR_ACCOUNT_APPROVAL

    assert approval.scope_values == frozenset({"account_status", "competition_catalogue"})
    assert approval.data_types == frozenset({"account_entitlements", "competition_catalogue"})
    assert approval.commercial_use_allowed is False
    assert approval.raw_redistribution_allowed is False

    allowed = evaluate_source_use(
        approval,
        DataUsePurpose.COLLECTION,
        scope_value="competition_catalogue",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
    )
    denied = evaluate_source_use(
        approval,
        DataUsePurpose.COLLECTION,
        scope_value="fixtures",
        at_utc=datetime(2026, 11, 16, tzinfo=UTC),
    )

    assert allowed.allowed is True
    assert denied.allowed is False



def test_the_odds_api_approval_is_exact_scope_and_noncommercial() -> None:
    approval = THE_ODDS_API_SOCCER_APPROVAL

    assert len(approval.scope_values) == 8
    assert approval.scope_type == "sport_key"
    assert approval.data_types == frozenset(
        {"sports_catalogue", "event_catalogue", "bookmaker_odds"}
    )
    assert approval.commercial_use_allowed is False
    assert approval.raw_redistribution_allowed is False

    allowed = evaluate_source_use(
        approval,
        DataUsePurpose.MODEL_TRAINING,
        scope_value="soccer_epl",
        at_utc=datetime(2026, 11, 18, tzinfo=UTC),
    )
    denied_scope = evaluate_source_use(
        approval,
        DataUsePurpose.MODEL_TRAINING,
        scope_value="soccer_uefa_champs_league",
        at_utc=datetime(2026, 11, 18, tzinfo=UTC),
    )
    denied_commercial = evaluate_source_use(
        approval,
        DataUsePurpose.MODEL_TRAINING,
        scope_value="soccer_epl",
        at_utc=datetime(2026, 11, 18, tzinfo=UTC),
        commercial=True,
    )
    denied_raw = evaluate_source_use(
        approval,
        DataUsePurpose.RAW_REDISTRIBUTION,
        scope_value="soccer_epl",
        at_utc=datetime(2026, 11, 18, tzinfo=UTC),
    )

    assert allowed.allowed is True
    assert denied_scope.reason_code == "SOURCE_SCOPE_NOT_APPROVED"
    assert denied_commercial.reason_code == "COMMERCIAL_USE_NOT_PERMITTED"
    assert denied_raw.reason_code == "RAW_REDISTRIBUTION_PROHIBITED"


def test_the_odds_api_approval_evidence_hash_matches_review() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    evidence = repository_root / "docs" / "providers" / "THE_ODDS_API_TERMS_REVIEW.md"

    assert sha256(evidence.read_bytes()).hexdigest() == THE_ODDS_API_SOCCER_APPROVAL.evidence_sha256
