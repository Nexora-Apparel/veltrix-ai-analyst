from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "backend/migrations/007_canonical_entity_layer.sql"


def test_canonical_schema_is_provenance_preserving_and_schema_only() -> None:
    sql = MIGRATION.read_text()
    required = (
        "CREATE TABLE veltrix_ai_analyst.canonical_teams",
        "CREATE TABLE veltrix_ai_analyst.canonical_competitions",
        "CREATE TABLE veltrix_ai_analyst.canonical_fixtures",
        "CREATE TABLE veltrix_ai_analyst.provider_team_identity_links",
        "CREATE TABLE veltrix_ai_analyst.provider_competition_identity_links",
        "CREATE TABLE veltrix_ai_analyst.canonical_fixture_sources",
        "CREATE TABLE veltrix_ai_analyst.canonical_identity_review_events",
        "enforce_canonical_link_provenance()",
        "validate_canonical_review_supersession()",
        "guard_canonical_fixture_source_merge()",
        "enforce_canonical_fixture_identity_status()",
    )
    for fragment in required:
        assert fragment in sql

    assert "source_observation_id" in sql
    assert "source_sighting_id" in sql
    assert "provider_response_id" in sql
    assert "rights_approval_id" in sql
    assert "payload_sha256" in sql
    assert "IS DISTINCT FROM 'SOURCE_FIXTURE_LINK_REVIEWED'" in sql
    assert "CANONICAL_FIXTURE_IDENTITY_LINKS_NOT_REVIEWED" in sql
    assert "CANONICAL_FIXTURE_SOURCE_FACTS_MISMATCH" in sql

    lowered = sql.lower()
    assert "insert into veltrix_ai_analyst.canonical_" not in lowered
    assert "update veltrix_ai_analyst.provider_fixtures" not in lowered
    assert "delete from veltrix_ai_analyst.provider_fixtures" not in lowered


def test_canonical_identity_decisions_are_append_only_and_event_driven() -> None:
    sql = MIGRATION.read_text()
    assert "mapping_status = 'REVIEW_REQUIRED'" in sql
    assert "canonical_identity_review_events_append_only" in sql
    assert "provider_team_identity_links_append_only" in sql
    assert "provider_competition_identity_links_append_only" in sql
    assert "canonical_fixture_sources_append_only" in sql
    assert "supersedes_event_id" in sql
    assert "CANONICAL_REVIEW_SUPERSESSION_TARGET_MISMATCH" in sql
