ALTER TABLE veltrix_ai_analyst.ingestion_quarantine
    ADD COLUMN entity_type TEXT NOT NULL DEFAULT 'SOURCE_RECORD'
        CHECK (entity_type IN ('SOURCE_RECORD', 'PROVIDER_PAGE')),
    ADD COLUMN request_key TEXT,
    ADD COLUMN http_status SMALLINT CHECK (
        http_status IS NULL OR http_status BETWEEN 100 AND 599
    ),
    ADD COLUMN provider_response_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT,
    ADD COLUMN response_sha256 CHAR(64) CHECK (
        response_sha256 IS NULL OR response_sha256 ~ '^[0-9a-f]{64}$'
    );

ALTER TABLE veltrix_ai_analyst.ingestion_quarantine
    ADD CONSTRAINT ingestion_quarantine_run_request_key_unique
    UNIQUE (import_run_id, request_key);
