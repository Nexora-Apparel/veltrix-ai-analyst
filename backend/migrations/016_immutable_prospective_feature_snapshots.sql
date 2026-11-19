-- Immutable, canonical-identity-backed point-in-time feature snapshots.
-- This stores research datasets only; it does not authorize prediction publication.

CREATE TABLE veltrix_ai_analyst.prospective_feature_snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    canonical_fixture_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_fixtures(id),
    canonical_competition_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_competitions(id),
    home_canonical_team_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_teams(id),
    away_canonical_team_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_teams(id),
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    provider_fixture_id TEXT NOT NULL,
    provider_competition_id TEXT NOT NULL,
    kickoff_at TIMESTAMPTZ NOT NULL,
    prediction_cutoff_at TIMESTAMPTZ NOT NULL,
    feature_schema_version TEXT NOT NULL,
    features JSONB NOT NULL,
    feature_lineage JSONB NOT NULL,
    label JSONB,
    label_observed_at TIMESTAMPTZ,
    label_observation_id BIGINT,
    label_lineage JSONB,
    snapshot_sha256 CHAR(64) NOT NULL,
    dataset_sha256 CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT prospective_feature_snapshots_cutoff_before_kickoff
        CHECK (prediction_cutoff_at < kickoff_at),
    CONSTRAINT prospective_feature_snapshots_distinct_teams
        CHECK (home_canonical_team_id <> away_canonical_team_id),
    CONSTRAINT prospective_feature_snapshots_feature_lineage_array
        CHECK (jsonb_typeof(feature_lineage) = 'array'),
    CONSTRAINT prospective_feature_snapshots_features_object
        CHECK (jsonb_typeof(features) = 'object'),
    CONSTRAINT prospective_feature_snapshots_sha256_check
        CHECK (
            snapshot_sha256 ~ '^[0-9a-f]{64}$'
            AND dataset_sha256 ~ '^[0-9a-f]{64}$'
        ),
    CONSTRAINT prospective_feature_snapshots_label_timing
        CHECK (
            (label IS NULL AND label_observed_at IS NULL AND label_observation_id IS NULL)
            OR
            (label IS NOT NULL AND label_observed_at IS NOT NULL
             AND label_observation_id IS NOT NULL AND label_observed_at > kickoff_at)
        ),
    CONSTRAINT prospective_feature_snapshots_idempotency_key
        UNIQUE (canonical_fixture_id, prediction_cutoff_at, feature_schema_version)
);

CREATE INDEX prospective_feature_snapshots_chronology_idx
    ON veltrix_ai_analyst.prospective_feature_snapshots
       (kickoff_at, prediction_cutoff_at, canonical_competition_id);

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.reject_prospective_snapshot_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'prospective feature snapshots are immutable';
END;
$$;

CREATE TRIGGER prospective_feature_snapshots_append_only
    BEFORE UPDATE OR DELETE
    ON veltrix_ai_analyst.prospective_feature_snapshots
    FOR EACH ROW
    EXECUTE FUNCTION veltrix_ai_analyst.reject_prospective_snapshot_mutation();
