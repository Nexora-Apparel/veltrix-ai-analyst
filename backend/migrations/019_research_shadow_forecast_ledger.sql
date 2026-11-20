-- Durable, append-only research forecasts. This ledger is deliberately separate
-- from production predictions/publication/settlement tables.
CREATE TABLE veltrix_ai_analyst.research_shadow_forecast_runs (
    run_key CHAR(64) PRIMARY KEY CHECK (run_key ~ '^[0-9a-f]{64}$'),
    generated_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'SHADOW_FORECASTS_READY',
        'NO_FRESH_UPCOMING_SNAPSHOTS',
        'INSUFFICIENT_CUTOFF_VALID_TRAINING_LABELS',
        'NO_VALID_SHADOW_FORECASTS'
    )),
    dataset_sha256 CHAR(64) NOT NULL CHECK (dataset_sha256 ~ '^[0-9a-f]{64}$'),
    training_data_sha256 CHAR(64)
        CHECK (training_data_sha256 IS NULL OR training_data_sha256 ~ '^[0-9a-f]{64}$'),
    training_cutoff_at TIMESTAMPTZ,
    training_fixture_count INTEGER NOT NULL DEFAULT 0 CHECK (training_fixture_count >= 0),
    model_version TEXT,
    code_commit CHAR(40) NOT NULL CHECK (code_commit ~ '^[0-9a-f]{40}$'),
    forecast_count INTEGER NOT NULL DEFAULT 0 CHECK (forecast_count BETWEEN 0 AND 25),
    abstention_count INTEGER NOT NULL DEFAULT 0 CHECK (abstention_count >= 0),
    report_sha256 CHAR(64) NOT NULL CHECK (report_sha256 ~ '^[0-9a-f]{64}$'),
    report JSONB NOT NULL CHECK (jsonb_typeof(report) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT statement_timestamp(),
    CHECK (
        status <> 'SHADOW_FORECASTS_READY'
        OR (
            training_data_sha256 IS NOT NULL
            AND training_cutoff_at IS NOT NULL
            AND training_fixture_count > 0
            AND model_version IS NOT NULL
            AND forecast_count > 0
        )
    )
);

CREATE INDEX research_shadow_forecast_runs_generated_idx
    ON veltrix_ai_analyst.research_shadow_forecast_runs(generated_at DESC);

CREATE TRIGGER research_shadow_forecast_runs_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.research_shadow_forecast_runs
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();
