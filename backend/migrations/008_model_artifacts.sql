CREATE TABLE IF NOT EXISTS veltrix_ai_analyst.model_artifacts (
    model_artifact_id TEXT PRIMARY KEY CHECK (length(model_artifact_id) BETWEEN 16 AND 160),
    model_family TEXT NOT NULL CHECK (length(model_family) BETWEEN 1 AND 100),
    model_version TEXT NOT NULL CHECK (length(model_version) BETWEEN 1 AND 80),
    training_data_fingerprint CHAR(64) NOT NULL
        CHECK (training_data_fingerprint ~ '^[0-9a-f]{64}$'),
    training_fixture_count INTEGER NOT NULL CHECK (training_fixture_count > 0),
    distinct_team_count INTEGER NOT NULL CHECK (distinct_team_count >= 2),
    training_cutoff_at TIMESTAMPTZ NOT NULL,
    point_in_time_certified BOOLEAN NOT NULL DEFAULT FALSE,
    owner_rights_declaration_id TEXT NOT NULL,
    artifact JSONB NOT NULL CHECK (jsonb_typeof(artifact) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (model_family, model_version, training_data_fingerprint)
);

CREATE INDEX IF NOT EXISTS model_artifacts_created_at_idx
    ON veltrix_ai_analyst.model_artifacts (created_at DESC);
