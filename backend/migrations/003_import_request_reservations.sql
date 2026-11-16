-- Durable idempotent reservation ledger for provider requests.
-- The import_runs row is the serialized budget authority; each reservation
-- commits before the caller performs the network request.
CREATE TABLE veltrix_ai_analyst.import_request_reservations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_run_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.import_runs(id) ON DELETE RESTRICT,
    request_key TEXT NOT NULL CHECK (length(btrim(request_key)) > 0),
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    page_number INTEGER NOT NULL CHECK (page_number > 0),
    endpoint TEXT NOT NULL CHECK (left(endpoint, 1) = '/' AND position('?' IN endpoint) = 0),
    params_sha256 CHAR(64) NOT NULL CHECK (params_sha256 ~ '^[0-9a-f]{64}$'),
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (import_run_id, request_key),
    CHECK (window_end > window_start)
);

CREATE INDEX import_request_reservations_run_idx
    ON veltrix_ai_analyst.import_request_reservations(import_run_id, reserved_at);

-- The initial historical collection envelope is deliberately hard-capped at 40
-- requests in the database, so application misconfiguration cannot raise it.
ALTER TABLE veltrix_ai_analyst.import_runs
    ADD CONSTRAINT import_runs_request_budget_ceiling
    CHECK (request_budget <= 40);
