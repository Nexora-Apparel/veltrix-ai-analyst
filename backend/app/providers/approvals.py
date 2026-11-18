"""Reviewed source approvals for the currently qualified Stage 2 datasets.

Keep scopes exact. Adding a competition, dataset path, use purpose or commercial
permission requires a new review and a corresponding evidence update.
"""
from datetime import UTC, datetime

from app.providers.rights import ApprovalStatus, DataUsePurpose, SourceApproval

FIVEDOLLAR_COMMUNITY_APPROVAL = SourceApproval(
    approval_id="approval-5dollar-community-fixtures-2026-11-12",
    provider="5DollarFootballAPI",
    source_id="5dollarfootballapi",
    scope_type="competition_id",
    scope_values=frozenset(
        {
            "3118717965",  # Brazil Serie A
            "522514093",  # Brazil Serie B
            "4160026622",  # England Premier League
            "3614399544",  # France Ligue 1
            "686337048",  # Germany Bundesliga I
            "3405541143",  # Italy Serie A
            "4212821298",  # Spain La Liga
        }
    ),
    data_types=frozenset(
        {"fixtures_and_results", "competition_catalogue", "team_catalogue"}
    ),
    status=ApprovalStatus.APPROVED,
    permitted_uses=frozenset(
        {
            DataUsePurpose.COLLECTION,
            DataUsePurpose.STORAGE,
            DataUsePurpose.HISTORICAL_IMPORT,
            DataUsePurpose.INTERNAL_ANALYSIS,
            DataUsePurpose.FEATURE_ENGINEERING,
            DataUsePurpose.MODEL_TRAINING,
            DataUsePurpose.MODEL_VALIDATION,
            DataUsePurpose.BENCHMARKING,
            DataUsePurpose.CACHE,
            DataUsePurpose.PUBLIC_DISPLAY,
        }
    ),
    commercial_use_allowed=False,
    terms_url="https://5dollarfootballapi.com/terms",
    terms_version="October 2026",
    evidence_uri="docs/providers/5DOLLAR_TERMS_REVIEW.md",
    evidence_sha256="e818940f894b924ec3e25fbf36e3a43e3969b17d509b21b7a476ddf14a10d879",
    rights_basis="TERMS",
    reviewed_at_utc=datetime(2026, 11, 12, tzinfo=UTC),
    reviewer_id="project-owner",
    valid_from_utc=datetime(2026, 11, 12, tzinfo=UTC),
    attribution_required=True,
    attribution_text="Football data by 5DollarFootballAPI",
    attribution_url="https://5dollarfootballapi.com",
    raw_redistribution_allowed=False,
)


FIVEDOLLAR_ACCOUNT_APPROVAL = SourceApproval(
    approval_id="approval-5dollar-community-account-metadata-2026-11-12",
    provider="5DollarFootballAPI",
    source_id="5dollarfootballapi",
    scope_type="account_resource",
    scope_values=frozenset({"account_status", "competition_catalogue"}),
    data_types=frozenset({"account_entitlements", "competition_catalogue"}),
    status=ApprovalStatus.APPROVED,
    permitted_uses=frozenset(
        {
            DataUsePurpose.COLLECTION,
            DataUsePurpose.STORAGE,
            DataUsePurpose.INTERNAL_ANALYSIS,
            DataUsePurpose.CACHE,
            DataUsePurpose.PUBLIC_DISPLAY,
        }
    ),
    commercial_use_allowed=False,
    terms_url="https://5dollarfootballapi.com/terms",
    terms_version="October 2026",
    evidence_uri="docs/providers/5DOLLAR_TERMS_REVIEW.md",
    evidence_sha256="e818940f894b924ec3e25fbf36e3a43e3969b17d509b21b7a476ddf14a10d879",
    rights_basis="TERMS",
    reviewed_at_utc=datetime(2026, 11, 12, tzinfo=UTC),
    reviewer_id="project-owner",
    valid_from_utc=datetime(2026, 11, 12, tzinfo=UTC),
    attribution_required=True,
    attribution_text="Football data by 5DollarFootballAPI",
    attribution_url="https://5dollarfootballapi.com",
    raw_redistribution_allowed=False,
)


AIMIDAS_BRAZIL_SERIE_B_APPROVAL = SourceApproval(
    approval_id="approval-aimidas-football-data-noncommercial-2026-11-15",
    provider="AI Midas Football Data",
    source_id="ai-midas-github-csv",
    scope_type="dataset_path",
    scope_values=frozenset({"advanced stats/Brazil Serie B 2026.csv"}),
    data_types=frozenset({"advanced_team_match_csv"}),
    status=ApprovalStatus.APPROVED,
    permitted_uses=frozenset(
        {
            DataUsePurpose.COLLECTION,
            DataUsePurpose.STORAGE,
            DataUsePurpose.HISTORICAL_IMPORT,
            DataUsePurpose.INTERNAL_ANALYSIS,
            DataUsePurpose.FEATURE_ENGINEERING,
            DataUsePurpose.MODEL_TRAINING,
            DataUsePurpose.MODEL_VALIDATION,
            DataUsePurpose.BENCHMARKING,
            DataUsePurpose.CACHE,
            DataUsePurpose.PUBLIC_DISPLAY,
        }
    ),
    commercial_use_allowed=False,
    terms_url=(
        "https://github.com/Nexora-Apparel/veltrix-football/blob/"
        "5b887c03604f45f6972bbf6c53613f064264e528/docs/legal/"
        "veltrix-all-source-noncommercial-authorization-2026-11-15.md"
    ),
    terms_version="USER_CONFIRMATION_2026-11-15",
    evidence_uri=(
        "https://github.com/Nexora-Apparel/veltrix-football/blob/"
        "5b887c03604f45f6972bbf6c53613f064264e528/docs/legal/"
        "veltrix-all-source-noncommercial-authorization-2026-11-15.md"
    ),
    evidence_sha256="c4e227329b08e7d75db41cc197a9c073f99100b3b1dc5930d68ad591cfc1f7c7",
    rights_basis="WRITTEN_PERMISSION",
    reviewed_at_utc=datetime(2026, 11, 15, tzinfo=UTC),
    reviewer_id="project-owner",
    valid_from_utc=datetime(2026, 11, 15, tzinfo=UTC),
    attribution_required=True,
    attribution_text="AI Midas Football Data",
    attribution_url="https://github.com/aimidas1/aimidas1",
    raw_redistribution_allowed=False,
)


THE_ODDS_API_SOCCER_APPROVAL = SourceApproval(
    approval_id="approval-the-odds-api-v4-soccer-2026-11-18",
    provider="The Odds API",
    source_id="the-odds-api-v4",
    scope_type="sport_key",
    scope_values=frozenset(
        {
            "soccer_brazil_campeonato",
            "soccer_brazil_serie_b",
            "soccer_epl",
            "soccer_france_ligue_one",
            "soccer_germany_bundesliga",
            "soccer_italy_serie_a",
            "soccer_spain_la_liga",
        }
    ),
    data_types=frozenset(
        {"sports_catalogue", "event_catalogue", "bookmaker_odds"}
    ),
    status=ApprovalStatus.APPROVED,
    permitted_uses=frozenset(
        {
            DataUsePurpose.COLLECTION,
            DataUsePurpose.STORAGE,
            DataUsePurpose.INTERNAL_ANALYSIS,
            DataUsePurpose.FEATURE_ENGINEERING,
            DataUsePurpose.MODEL_TRAINING,
            DataUsePurpose.MODEL_VALIDATION,
            DataUsePurpose.BENCHMARKING,
            DataUsePurpose.CACHE,
            DataUsePurpose.PUBLIC_DISPLAY,
        }
    ),
    commercial_use_allowed=False,
    terms_url="https://the-odds-api.com/terms-and-conditions.html",
    terms_version="2026-08-31",
    evidence_uri="docs/providers/THE_ODDS_API_TERMS_REVIEW.md",
    evidence_sha256="b1a4862960bf478118091706f13b09b6b97606b77819ef21f858592c424d8742",
    rights_basis="TERMS",
    reviewed_at_utc=datetime(2026, 11, 18, tzinfo=UTC),
    reviewer_id="project-owner",
    valid_from_utc=datetime(2026, 11, 18, tzinfo=UTC),
    attribution_required=False,
    attribution_text="Odds data by The Odds API",
    attribution_url="https://the-odds-api.com",
    raw_redistribution_allowed=False,
)
