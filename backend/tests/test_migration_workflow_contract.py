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


def test_migration_008_scopes_fixture_only_trigger_fields() -> None:
    migration = (ROOT / "backend/migrations/008_canonical_identity_link_uniqueness.sql").read_text()
    assert "CREATE OR REPLACE FUNCTION veltrix_ai_analyst.enforce_canonical_link_provenance()" in migration
    assert "expected_data_type := 'team_catalogue'" in migration
    assert "expected_data_type := 'competition_catalogue'" in migration
    assert "expected_data_type := 'fixtures_and_results'" in migration
    assert "IF TG_TABLE_NAME = 'canonical_fixture_sources' THEN\n        IF NOT EXISTS (" in migration
    assert "enforce_canonical_link_provenance()" in (
        ROOT / ".github/workflows/apply-database-migrations.yml"
    ).read_text()

def test_manual_migration_workflow_verifies_system_observed_pit_migration() -> None:
    workflow = (ROOT / ".github/workflows/apply-database-migrations.yml").read_text()
    migration = (ROOT / "backend/migrations/010_system_observed_pit.sql").read_text()
    assert "010_system_observed_pit.sql" in workflow
    assert "source_observations_pit_evidence_check" in workflow
    assert "source_observation_sightings_pit_evidence_check" in workflow
    assert "SYSTEM_OBSERVED_AT" in migration
    assert "available_at = retrieved_at" in migration
    assert "sighting.retrieved_at > NEW.prediction_cutoff_at" in migration
    assert "source_published_at IS NULL" in migration



def test_manual_migration_workflow_verifies_system_observed_pit_migration_010() -> None:
    workflow = (ROOT / ".github/workflows/apply-database-migrations.yml").read_text()
    migration = (ROOT / "backend/migrations/010_system_observed_pit.sql").read_text()
    assert "010_system_observed_pit.sql" in workflow
    assert "source_observations_pit_evidence_check" in workflow
    assert "source_observation_sightings_pit_evidence_check" in workflow
    assert "SYSTEM_OBSERVED_AT" in migration
    assert "sighting.available_at <> sighting.retrieved_at" in migration
    assert "PRE_MATCH_SYSTEM_OBSERVATION_NOT_AVAILABLE_AT_CUTOFF" in migration


def test_prediction_settlement_migration_is_append_only_and_provenance_gated() -> None:
    migration = (
        ROOT / "backend/migrations/018_prediction_settlement_ledger.sql"
    ).read_text()
    assert "CREATE TABLE veltrix_ai_analyst.prediction_settlement_events" in migration
    assert "UNIQUE (prediction_id, source_observation_id)" in migration
    assert "enforce_prediction_settlement_evidence()" in migration
    assert "prediction_settlement_evidence_guard" in migration
    assert "prediction_settlement_events_append_only" in migration
    assert "latest_prediction_settlements" in migration
    assert "SYSTEM_OBSERVED_AT" in migration
    assert "observation_pit_certifiable IS NOT TRUE" in migration
    assert "MODEL_TRAINING" in migration
    assert "MODEL_VALIDATION" in migration
    assert "SOURCE_FIXTURE_LINK_REVIEWED" in migration
    assert "PREDICTION_SETTLEMENT_TIME_NOT_MONOTONIC" in migration
    assert "provider_response_sha256" in migration
    assert "source_payload_sha256" in migration


def test_manual_migration_workflow_verifies_prediction_settlement_migration() -> None:
    workflow = (
        ROOT / ".github/workflows/apply-database-migrations.yml"
    ).read_text()
    assert "018_prediction_settlement_ledger.sql" in workflow
    assert "prediction_settlement_events" in workflow
    assert "latest_prediction_settlements" in workflow
    assert "enforce_prediction_settlement_evidence()" in workflow
    assert "prediction_settlement_evidence_guard" in workflow
    assert "prediction_settlement_events_append_only" in workflow


def test_settlement_workflow_is_scheduled_and_manual_execution_is_opt_in() -> None:
    workflow = (
        ROOT / ".github/workflows/settle-published-predictions.yml"
    ).read_text()
    assert 'cron: "0 6 * * *"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "execute_settlements:" in workflow
    assert "default: false" in workflow
    assert 'GITHUB_EVENT_NAME" == "schedule"' in workflow
    assert 'EXECUTE_SETTLEMENTS" == "true"' in workflow
    assert "scripts/settle_published_predictions.py" in workflow
    assert "VELTRIX_AI_ANALYST_DATABASE_URL" in workflow
    assert "The Odds API" not in workflow
