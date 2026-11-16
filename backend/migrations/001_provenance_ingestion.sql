-- VELTRIX AI ANALYST Stage 2: provenance-first ingestion foundation.
-- Provider IDs remain provider-local. No cross-provider fixture merging occurs here.

CREATE SCHEMA IF NOT EXISTS veltrix_ai_analyst;

CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version TEXT PRIMARY KEY,
    checksum CHAR(64) NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE veltrix_ai_analyst.source_approvals (
    approval_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    scope_type TEXT NOT NULL,
    scope_values JSONB NOT NULL
        CHECK (jsonb_typeof(scope_values) = 'array' AND jsonb_array_length(scope_values) > 0),
    data_types JSONB NOT NULL
        CHECK (jsonb_typeof(data_types) = 'array' AND jsonb_array_length(data_types) > 0),
    status TEXT NOT NULL CHECK (status IN ('APPROVED', 'PROVISIONAL', 'REVOKED')),
    rights_basis TEXT CHECK (rights_basis IN ('TERMS', 'WRITTEN_PERMISSION', 'OPEN_LICENSE', 'CONTRACT')),
    terms_url TEXT,
    terms_version TEXT,
    evidence_uri TEXT,
    evidence_sha256 CHAR(64) CHECK (
        evidence_sha256 IS NULL OR evidence_sha256 ~ '^[0-9a-f]{64}$'
    ),
    reviewed_at TIMESTAMPTZ,
    reviewer_id TEXT,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    permitted_uses JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(permitted_uses) = 'array'),
    commercial_use_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    attribution_required BOOLEAN NOT NULL DEFAULT FALSE,
    attribution_text TEXT,
    attribution_url TEXT,
    raw_redistribution_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (valid_until IS NULL OR valid_until > valid_from),
    CHECK (
        NOT (scope_values @> '["*"]'::jsonb)
        AND NOT (scope_values @> '["all"]'::jsonb)
    ),
    CHECK (
        status <> 'APPROVED'
        OR (
            rights_basis IS NOT NULL
            AND terms_url IS NOT NULL AND terms_url <> ''
            AND terms_version IS NOT NULL AND terms_version <> ''
            AND evidence_uri IS NOT NULL AND evidence_uri <> ''
            AND evidence_sha256 IS NOT NULL
            AND reviewed_at IS NOT NULL
            AND reviewer_id IS NOT NULL AND reviewer_id <> ''
            AND jsonb_array_length(permitted_uses) > 0
        )
    ),
    CHECK (
        NOT attribution_required
        OR (
            attribution_text IS NOT NULL AND attribution_text <> ''
            AND attribution_url IS NOT NULL AND attribution_url <> ''
        )
    )
);

CREATE UNIQUE INDEX source_approvals_version_idx
    ON veltrix_ai_analyst.source_approvals
    (provider, source_id, scope_type, scope_values, data_types, terms_version, evidence_sha256);

CREATE TABLE veltrix_ai_analyst.source_approval_status_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (status IN ('APPROVED', 'REVOKED')),
    evidence_uri TEXT NOT NULL,
    evidence_sha256 CHAR(64) NOT NULL CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    effective_at TIMESTAMPTZ NOT NULL,
    reason_code TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (approval_id, status, evidence_sha256)
);

CREATE OR REPLACE VIEW veltrix_ai_analyst.effective_source_approvals AS
SELECT
    approval.*,
    COALESCE(latest_event.status, approval.status) AS effective_status,
    COALESCE(latest_event.effective_at, approval.valid_from) AS effective_status_at
FROM veltrix_ai_analyst.source_approvals AS approval
LEFT JOIN LATERAL (
    SELECT event.status, event.effective_at
    FROM veltrix_ai_analyst.source_approval_status_events AS event
    WHERE event.approval_id = approval.approval_id
      AND event.effective_at <= CURRENT_TIMESTAMP
    ORDER BY event.effective_at DESC, event.id DESC
    LIMIT 1
) AS latest_event ON TRUE;

CREATE TABLE veltrix_ai_analyst.provider_responses (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    request_id TEXT NOT NULL,
    request_params JSONB NOT NULL DEFAULT '{}'::jsonb,
    http_status SMALLINT NOT NULL CHECK (http_status BETWEEN 100 AND 599),
    response_sha256 CHAR(64) NOT NULL CHECK (response_sha256 ~ '^[0-9a-f]{64}$'),
    raw_body BYTEA NOT NULL CHECK (octet_length(raw_body) > 0),
    response_headers JSONB NOT NULL DEFAULT '{}'::jsonb,
    quota_limit INTEGER CHECK (quota_limit IS NULL OR quota_limit >= 0),
    quota_remaining INTEGER CHECK (quota_remaining IS NULL OR quota_remaining >= 0),
    quota_reset_at TIMESTAMPTZ,
    rights_approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    fetched_at TIMESTAMPTZ NOT NULL,
    retention_until TIMESTAMPTZ,
    UNIQUE (provider, source_id, request_id, response_sha256),
    CHECK (retention_until IS NULL OR retention_until > fetched_at)
);
CREATE INDEX provider_responses_provider_time_idx
    ON veltrix_ai_analyst.provider_responses(provider, source_id, fetched_at DESC);

CREATE TABLE veltrix_ai_analyst.provider_request_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    request_params JSONB NOT NULL DEFAULT '{}'::jsonb,
    http_status SMALLINT CHECK (http_status IS NULL OR http_status BETWEEN 100 AND 599),
    retry_after_seconds DOUBLE PRECISION CHECK (
        retry_after_seconds IS NULL OR retry_after_seconds >= 0
    ),
    quota_remaining INTEGER CHECK (quota_remaining IS NULL OR quota_remaining >= 0),
    provider_response_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);
CREATE INDEX provider_request_events_window_idx
    ON veltrix_ai_analyst.provider_request_events(provider, source_id, started_at DESC);

CREATE TABLE veltrix_ai_analyst.provider_entitlement_observations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    plan_code TEXT NOT NULL,
    entitlement_status TEXT NOT NULL,
    country_pack_code TEXT,
    competition_ids JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(competition_ids) = 'array'),
    rate_limit_hour INTEGER CHECK (rate_limit_hour IS NULL OR rate_limit_hour >= 0),
    rate_limit_minute INTEGER CHECK (rate_limit_minute IS NULL OR rate_limit_minute >= 0),
    quota_remaining INTEGER CHECK (quota_remaining IS NULL OR quota_remaining >= 0),
    provider_response_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT,
    evidence_sha256 CHAR(64) NOT NULL CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    checked_at TIMESTAMPTZ NOT NULL,
    UNIQUE (provider, source_id, checked_at, evidence_sha256)
);
CREATE INDEX provider_entitlement_history_idx
    ON veltrix_ai_analyst.provider_entitlement_observations(provider, source_id, checked_at DESC);

CREATE TABLE veltrix_ai_analyst.source_observations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    data_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    provider_entity_id TEXT NOT NULL,
    payload_sha256 CHAR(64) NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    schema_version TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    source_updated_at TIMESTAMPTZ,
    source_event_time TIMESTAMPTZ,
    source_published_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ,
    availability_basis TEXT NOT NULL CHECK (
        availability_basis IN (
            'SOURCE_PUBLISHED_AT',
            'SOURCE_EVENT_TIME',
            'FOUR_DAY_POST_KICKOFF_PROXY',
            'RETRIEVED_AT_ONLY',
            'UNVERIFIED',
            'NONE'
        )
    ),
    point_in_time_certifiable BOOLEAN NOT NULL DEFAULT FALSE,
    rights_approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    provider_response_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT,
    payload JSONB NOT NULL,
    UNIQUE (provider, source_id, data_type, entity_type, provider_entity_id, payload_sha256),
    CHECK (
        NOT point_in_time_certifiable
        OR (
            source_published_at IS NOT NULL
            AND availability_basis = 'SOURCE_PUBLISHED_AT'
        )
    )
);
CREATE INDEX source_observations_lookup_idx
    ON veltrix_ai_analyst.source_observations
    (provider, source_id, data_type, entity_type, provider_entity_id, retrieved_at DESC);

CREATE TABLE veltrix_ai_analyst.provider_competitions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    provider_competition_id TEXT NOT NULL,
    name TEXT NOT NULL,
    country_code TEXT,
    country_name TEXT,
    seasons JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(seasons) = 'array'),
    is_popular BOOLEAN,
    has_standings BOOLEAN,
    last_fixture_at TIMESTAMPTZ,
    source_observation_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observations(id) ON DELETE RESTRICT,
    rights_approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    UNIQUE (provider, source_id, provider_competition_id),
    CHECK (last_seen_at >= first_seen_at)
);

CREATE TABLE veltrix_ai_analyst.provider_teams (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    provider_team_id TEXT NOT NULL,
    name TEXT NOT NULL,
    country_code TEXT,
    source_observation_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observations(id) ON DELETE RESTRICT,
    rights_approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    UNIQUE (provider, source_id, provider_team_id),
    CHECK (last_seen_at >= first_seen_at)
);

CREATE TABLE veltrix_ai_analyst.provider_fixtures (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    provider_fixture_id TEXT NOT NULL,
    provider_competition_id TEXT NOT NULL,
    home_team_provider_id TEXT NOT NULL,
    away_team_provider_id TEXT NOT NULL,
    home_team_name TEXT,
    away_team_name TEXT,
    kickoff_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('SCHEDULED', 'LIVE', 'FINISHED', 'POSTPONED', 'CANCELLED', 'ABANDONED', 'UNKNOWN')
    ),
    status_reason TEXT,
    status_code TEXT,
    home_goals SMALLINT CHECK (home_goals IS NULL OR home_goals >= 0),
    away_goals SMALLINT CHECK (away_goals IS NULL OR away_goals >= 0),
    home_corners SMALLINT CHECK (home_corners IS NULL OR home_corners >= 0),
    away_corners SMALLINT CHECK (away_corners IS NULL OR away_corners >= 0),
    home_yellow_cards SMALLINT CHECK (home_yellow_cards IS NULL OR home_yellow_cards >= 0),
    away_yellow_cards SMALLINT CHECK (away_yellow_cards IS NULL OR away_yellow_cards >= 0),
    home_red_cards SMALLINT CHECK (home_red_cards IS NULL OR home_red_cards >= 0),
    away_red_cards SMALLINT CHECK (away_red_cards IS NULL OR away_red_cards >= 0),
    source_observation_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observations(id) ON DELETE RESTRICT,
    rights_approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    UNIQUE (provider, source_id, provider_fixture_id),
    FOREIGN KEY (provider, source_id, provider_competition_id)
        REFERENCES veltrix_ai_analyst.provider_competitions
        (provider, source_id, provider_competition_id) ON DELETE RESTRICT,
    FOREIGN KEY (provider, source_id, home_team_provider_id)
        REFERENCES veltrix_ai_analyst.provider_teams
        (provider, source_id, provider_team_id) ON DELETE RESTRICT,
    FOREIGN KEY (provider, source_id, away_team_provider_id)
        REFERENCES veltrix_ai_analyst.provider_teams
        (provider, source_id, provider_team_id) ON DELETE RESTRICT,
    CHECK (home_team_provider_id <> away_team_provider_id),
    CHECK (last_seen_at >= first_seen_at),
    CHECK (
        (status = 'FINISHED' AND home_goals IS NOT NULL AND away_goals IS NOT NULL)
        OR
        (status <> 'FINISHED' AND home_goals IS NULL AND away_goals IS NULL)
    )
);
CREATE INDEX provider_fixtures_kickoff_idx
    ON veltrix_ai_analyst.provider_fixtures(kickoff_at);
CREATE INDEX provider_fixtures_competition_kickoff_idx
    ON veltrix_ai_analyst.provider_fixtures(provider, source_id, provider_competition_id, kickoff_at);

CREATE TABLE veltrix_ai_analyst.import_runs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    import_type TEXT NOT NULL,
    boundary_start TIMESTAMPTZ NOT NULL,
    boundary_end TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('PLANNED', 'RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED', 'PAUSED')
    ),
    importer_version TEXT NOT NULL,
    manifest_sha256 CHAR(64) CHECK (
        manifest_sha256 IS NULL OR manifest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    request_budget INTEGER NOT NULL CHECK (request_budget >= 0),
    requests_used INTEGER NOT NULL DEFAULT 0 CHECK (requests_used >= 0),
    records_seen INTEGER NOT NULL DEFAULT 0 CHECK (records_seen >= 0),
    records_inserted INTEGER NOT NULL DEFAULT 0 CHECK (records_inserted >= 0),
    records_duplicate INTEGER NOT NULL DEFAULT 0 CHECK (records_duplicate >= 0),
    records_rejected INTEGER NOT NULL DEFAULT 0 CHECK (records_rejected >= 0),
    records_quarantined INTEGER NOT NULL DEFAULT 0 CHECK (records_quarantined >= 0),
    rights_approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    reason_code TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (boundary_end > boundary_start),
    CHECK (requests_used <= request_budget),
    CHECK (records_seen >= records_inserted + records_duplicate + records_rejected + records_quarantined),
    CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
);
CREATE INDEX import_runs_provider_status_idx
    ON veltrix_ai_analyst.import_runs(provider, source_id, status, created_at DESC);

CREATE TABLE veltrix_ai_analyst.import_checkpoints (
    import_run_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.import_runs(id) ON DELETE RESTRICT,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    cursor_value TEXT,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')),
    records_seen INTEGER NOT NULL DEFAULT 0 CHECK (records_seen >= 0),
    records_inserted INTEGER NOT NULL DEFAULT 0 CHECK (records_inserted >= 0),
    records_duplicate INTEGER NOT NULL DEFAULT 0 CHECK (records_duplicate >= 0),
    records_rejected INTEGER NOT NULL DEFAULT 0 CHECK (records_rejected >= 0),
    records_quarantined INTEGER NOT NULL DEFAULT 0 CHECK (records_quarantined >= 0),
    requests_used INTEGER NOT NULL DEFAULT 0 CHECK (requests_used >= 0),
    response_sha256 CHAR(64) CHECK (
        response_sha256 IS NULL OR response_sha256 ~ '^[0-9a-f]{64}$'
    ),
    last_error_code TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (import_run_id, window_start, window_end),
    CHECK (window_end > window_start),
    CHECK (records_seen >= records_inserted + records_duplicate + records_rejected + records_quarantined)
);

CREATE TABLE veltrix_ai_analyst.sync_watermarks (
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    data_class TEXT NOT NULL,
    scope TEXT NOT NULL,
    cursor_value TEXT,
    version BIGINT NOT NULL DEFAULT 0 CHECK (version >= 0),
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (provider, source_id, data_class, scope)
);

CREATE TABLE veltrix_ai_analyst.ingestion_quarantine (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    provider_entity_id TEXT NOT NULL,
    source_observation_id BIGINT
        REFERENCES veltrix_ai_analyst.source_observations(id) ON DELETE RESTRICT,
    import_run_id BIGINT
        REFERENCES veltrix_ai_analyst.import_runs(id) ON DELETE RESTRICT,
    reason_code TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolution_evidence TEXT,
    CHECK (resolved_at IS NULL OR resolved_at >= created_at)
);
CREATE INDEX ingestion_quarantine_open_idx
    ON veltrix_ai_analyst.ingestion_quarantine(provider, source_id, created_at DESC)
    WHERE resolved_at IS NULL;

CREATE TABLE veltrix_ai_analyst.import_run_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_run_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.import_runs(id) ON DELETE RESTRICT,
    event_type TEXT NOT NULL,
    event_at TIMESTAMPTZ NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'IMMUTABLE_HISTORY_RECORD: % is append-only', TG_TABLE_NAME;
END;
$$;

CREATE TRIGGER source_approvals_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.source_approvals
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE TRIGGER source_approval_events_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.source_approval_status_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE TRIGGER provider_responses_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.provider_responses
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE TRIGGER provider_entitlements_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.provider_entitlement_observations
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE TRIGGER source_observations_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.source_observations
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE TRIGGER provider_request_events_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.provider_request_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE TRIGGER import_run_events_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.import_run_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();
