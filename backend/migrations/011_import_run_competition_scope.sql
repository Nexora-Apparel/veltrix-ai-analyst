-- Persist the exact approved competition scope on every historical import run.
-- Existing runs remain NULL until independently reconciled; do not infer their scope.

ALTER TABLE veltrix_ai_analyst.import_runs
    ADD COLUMN scope_value TEXT;

ALTER TABLE veltrix_ai_analyst.import_runs
    ADD CONSTRAINT import_runs_scope_value_nonblank_check
    CHECK (scope_value IS NULL OR length(btrim(scope_value)) > 0);

COMMENT ON COLUMN veltrix_ai_analyst.import_runs.scope_value IS
    'Exact source approval scope value (e.g. provider competition ID); NULL only for legacy runs created before migration 011.';
