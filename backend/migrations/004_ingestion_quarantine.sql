CREATE TABLE veltrix_ai_analyst.ingestion_quarantine (
    id BIGSERIAL PRIMARY KEY,
    import_run_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.import_runs(id) ON DELETE RESTRICT,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type = 'PROVIDER_PAGE'),
    provider_entity_id TEXT NOT NULL,
    request_key TEXT NOT NULL,
    reason_code TEXT NOT NULL CHECK (reason_code ~ '^[A-Z0-9_]+$'),
    http_status INTEGER CHECK (http_status IS NULL OR http_status BETWEEN 100 AND 599),
    provider_response_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT,
    response_sha256 CHAR(64) CHECK (
        response_sha256 IS NULL OR response_sha256 ~ '^[0-9a-f]{64}$'
    ),
    details JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(details) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (import_run_id, request_key)
);

CREATE INDEX ingestion_quarantine_run_created_idx
    ON veltrix_ai_analyst.ingestion_quarantine(import_run_id, created_at);

CREATE TRIGGER ingestion_quarantine_immutable
BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.ingestion_quarantine
FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();
