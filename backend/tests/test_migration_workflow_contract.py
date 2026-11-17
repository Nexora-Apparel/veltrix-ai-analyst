from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_manual_migration_workflow_uses_checksum_runner_and_exact_database() -> None:
    workflow = (ROOT / ".github/workflows/apply-database-migrations.yml").read_text()
    assert "workflow_dispatch:" in workflow
    assert "APPLY_CHECKSUM_VERIFIED_MIGRATIONS" in workflow
    assert 'from app.db.migrations import apply_migrations' in workflow
    assert 'expected_database="veltrix_ai_analyst"' in workflow
    assert "allow_remote=True" in workflow
    assert "FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY" not in workflow
    assert "collect_brazil_serie_b_history.py" not in workflow


def test_manual_migration_workflow_verifies_migration_006_objects() -> None:
    workflow = (ROOT / ".github/workflows/apply-database-migrations.yml").read_text()
    assert "006_pre_match_feature_pit_gate.sql" in workflow
    assert "MIGRATION_CHECKSUM_VERIFICATION_FAILED" in workflow
    assert "pre_match_feature_observations" in workflow
    assert "enforce_pre_match_feature_pit()" in workflow
    assert "pre_match_feature_pit_guard" in workflow
    assert "pre_match_feature_observations_append_only" in workflow



def test_manual_migration_workflow_verifies_canonical_migration_007() -> None:
    workflow = (ROOT / ".github/workflows/apply-database-migrations.yml").read_text()
    assert "007_canonical_entity_layer.sql" in workflow
    assert "canonical_identity_review_events" in workflow
    assert "canonical_fixture_identity_status_guard" in workflow
    assert "canonical_fixture_source_merge_guard" in workflow
    assert "MIGRATION_CHECKSUM_VERIFICATION_FAILED" in workflow

def test_manual_migration_workflow_verifies_canonical_link_uniqueness_008() -> None:
    workflow = (ROOT / ".github/workflows/apply-database-migrations.yml").read_text()
    migration = (ROOT / "backend/migrations/008_canonical_identity_link_uniqueness.sql").read_text()
    assert "008_canonical_identity_link_uniqueness.sql" in workflow
    assert "provider_team_identity_links_source_identity_uk" in workflow
    assert "provider_competition_identity_links_source_identity_uk" in workflow
    assert "MIGRATION_INDEX_VERIFICATION_FAILED" in workflow
    assert "CREATE UNIQUE INDEX provider_team_identity_links_source_identity_uk" in migration
    assert "CREATE UNIQUE INDEX provider_competition_identity_links_source_identity_uk" in migration
