-- Preserve every observation/retrieval link when an identical payload is deduplicated.
ALTER TABLE veltrix_ai_analyst.source_observations
    ADD CONSTRAINT source_observations_publication_before_retrieval
    CHECK (source_published_at IS NULL OR source_published_at <= retrieved_at);

CREATE TABLE veltrix_ai_analyst.source_observation_sightings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_observation_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observations(id) ON DELETE RESTRICT,
    provider_response_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT,
    retrieved_at TIMESTAMPTZ NOT NULL,
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
    payload_sha256 CHAR(64) NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (source_published_at IS NULL OR source_published_at <= retrieved_at),
    CHECK (
        NOT point_in_time_certifiable
        OR (
            source_published_at IS NOT NULL
            AND availability_basis = 'SOURCE_PUBLISHED_AT'
        )
    )
);

CREATE UNIQUE INDEX source_observation_sightings_response_idx
    ON veltrix_ai_analyst.source_observation_sightings
    (source_observation_id, provider_response_id, retrieved_at)
    WHERE provider_response_id IS NOT NULL;

CREATE UNIQUE INDEX source_observation_sightings_no_response_idx
    ON veltrix_ai_analyst.source_observation_sightings
    (source_observation_id, retrieved_at)
    WHERE provider_response_id IS NULL;

CREATE INDEX source_observation_sightings_timeline_idx
    ON veltrix_ai_analyst.source_observation_sightings
    (source_observation_id, retrieved_at DESC);

CREATE TRIGGER source_observation_sightings_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.source_observation_sightings
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();
