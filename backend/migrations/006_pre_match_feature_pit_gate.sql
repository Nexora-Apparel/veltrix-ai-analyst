-- VELTRIX AI ANALYST: database-enforced point-in-time gate for pre-match features.
-- No existing observations are upgraded or backfilled as PIT by this migration.

CREATE TABLE veltrix_ai_analyst.pre_match_feature_observations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_observation_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observations(id) ON DELETE RESTRICT,
    source_sighting_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observation_sightings(id) ON DELETE RESTRICT,
    feature_key TEXT NOT NULL CHECK (length(btrim(feature_key)) BETWEEN 1 AND 160),
    feature_value JSONB NOT NULL,
    prediction_cutoff_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_observation_id, source_sighting_id, feature_key, prediction_cutoff_at)
);

CREATE INDEX pre_match_feature_observations_cutoff_idx
    ON veltrix_ai_analyst.pre_match_feature_observations
    (prediction_cutoff_at, feature_key);

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.enforce_pre_match_feature_pit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    observation RECORD;
    sighting RECORD;
    approval RECORD;
    latest_approval_event RECORD;
BEGIN
    SELECT
        o.id,
        o.provider,
        o.source_id,
        o.payload_sha256,
        o.rights_approval_id
    INTO observation
    FROM veltrix_ai_analyst.source_observations o
    WHERE o.id = NEW.source_observation_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRE_MATCH_SOURCE_OBSERVATION_NOT_FOUND';
    END IF;

    SELECT
        s.id,
        s.source_observation_id,
        s.provider_response_id,
        s.retrieved_at,
        s.source_published_at,
        s.available_at,
        s.availability_basis,
        s.point_in_time_certifiable,
        s.payload_sha256
    INTO sighting
    FROM veltrix_ai_analyst.source_observation_sightings s
    WHERE s.id = NEW.source_sighting_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRE_MATCH_SOURCE_SIGHTING_NOT_FOUND';
    END IF;
    IF sighting.source_observation_id <> NEW.source_observation_id THEN
        RAISE EXCEPTION 'PRE_MATCH_SOURCE_SIGHTING_MISMATCH';
    END IF;

    IF sighting.point_in_time_certifiable IS NOT TRUE
       OR sighting.availability_basis <> 'SOURCE_PUBLISHED_AT'
       OR sighting.source_published_at IS NULL
       OR sighting.available_at IS NULL
       OR sighting.provider_response_id IS NULL
       OR sighting.payload_sha256 <> observation.payload_sha256 THEN
        RAISE EXCEPTION 'PRE_MATCH_SOURCE_PUBLICATION_EVIDENCE_REQUIRED';
    END IF;

    IF sighting.source_published_at > sighting.retrieved_at
       OR sighting.available_at < sighting.source_published_at
       OR sighting.available_at > NEW.prediction_cutoff_at
       OR sighting.source_published_at > NEW.prediction_cutoff_at THEN
        RAISE EXCEPTION 'PRE_MATCH_SOURCE_NOT_AVAILABLE_AT_CUTOFF';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM veltrix_ai_analyst.provider_responses r
        WHERE r.id = sighting.provider_response_id
          AND r.provider = observation.provider
          AND r.source_id = observation.source_id
          AND r.http_status BETWEEN 200 AND 299
    ) THEN
        RAISE EXCEPTION 'PRE_MATCH_RESPONSE_PROVENANCE_INVALID';
    END IF;

    SELECT a.*
    INTO approval
    FROM veltrix_ai_analyst.source_approvals a
    WHERE a.approval_id = observation.rights_approval_id;

    IF NOT FOUND
       OR approval.status <> 'APPROVED'
       OR approval.valid_from > NEW.prediction_cutoff_at
       OR (approval.valid_until IS NOT NULL AND approval.valid_until <= NEW.prediction_cutoff_at)
       OR NOT (approval.permitted_uses @> '["FEATURE_ENGINEERING", "MODEL_TRAINING"]'::jsonb) THEN
        RAISE EXCEPTION 'PRE_MATCH_SOURCE_RIGHTS_NOT_APPROVED_FOR_MODEL_FEATURES';
    END IF;

    SELECT e.status, e.effective_at
    INTO latest_approval_event
    FROM veltrix_ai_analyst.source_approval_status_events e
    WHERE e.approval_id = observation.rights_approval_id
      AND e.effective_at <= NEW.prediction_cutoff_at
    ORDER BY e.effective_at DESC, e.id DESC
    LIMIT 1;

    IF FOUND THEN
        IF latest_approval_event.status <> 'APPROVED' THEN
            RAISE EXCEPTION 'PRE_MATCH_SOURCE_RIGHTS_REVOKED_AT_CUTOFF';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER pre_match_feature_pit_guard
    BEFORE INSERT ON veltrix_ai_analyst.pre_match_feature_observations
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.enforce_pre_match_feature_pit();

CREATE TRIGGER pre_match_feature_observations_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.pre_match_feature_observations
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();
