-- Bind every feature snapshot to its target fixture so the database can
-- enforce a strict pre-kickoff prediction cutoff. The table is currently empty.
ALTER TABLE veltrix_ai_analyst.pre_match_feature_observations
    ADD COLUMN target_fixture_id BIGINT NOT NULL
    REFERENCES veltrix_ai_analyst.provider_fixtures(id) ON DELETE RESTRICT;

ALTER TABLE veltrix_ai_analyst.pre_match_feature_observations
    DROP CONSTRAINT pre_match_feature_observation_source_observation_id_source__key;
ALTER TABLE veltrix_ai_analyst.pre_match_feature_observations
    ADD CONSTRAINT pre_match_feature_observations_target_source_feature_key
    UNIQUE (
        target_fixture_id,
        source_observation_id,
        source_sighting_id,
        feature_key,
        prediction_cutoff_at
    );

CREATE INDEX pre_match_feature_observations_target_cutoff_idx
    ON veltrix_ai_analyst.pre_match_feature_observations (
        target_fixture_id, prediction_cutoff_at, feature_key
    );

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.enforce_pre_match_feature_pit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    observation RECORD;
    sighting RECORD;
    target_fixture RECORD;
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
        f.id,
        f.provider,
        f.source_id,
        f.provider_competition_id,
        f.kickoff_at
    INTO target_fixture
    FROM veltrix_ai_analyst.provider_fixtures f
    WHERE f.id = NEW.target_fixture_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRE_MATCH_TARGET_FIXTURE_NOT_FOUND';
    END IF;
    IF observation.provider <> target_fixture.provider
       OR observation.source_id <> target_fixture.source_id THEN
        RAISE EXCEPTION 'PRE_MATCH_TARGET_SOURCE_IDENTITY_MISMATCH';
    END IF;
    IF NEW.prediction_cutoff_at >= target_fixture.kickoff_at THEN
        RAISE EXCEPTION 'PRE_MATCH_TARGET_CUTOFF_NOT_BEFORE_KICKOFF';
    END IF;

    SELECT
        s.id,
        s.source_observation_id,
        s.provider_response_id,
        s.retrieved_at,
        s.source_published_at,
        s.available_at,
        s.system_observed_at,
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
       OR sighting.available_at IS NULL
       OR sighting.provider_response_id IS NULL
       OR sighting.payload_sha256 <> observation.payload_sha256 THEN
        RAISE EXCEPTION 'PRE_MATCH_SOURCE_AVAILABILITY_EVIDENCE_REQUIRED';
    END IF;

    IF sighting.availability_basis = 'SOURCE_PUBLISHED_AT' THEN
        IF sighting.source_published_at IS NULL
           OR sighting.source_published_at > sighting.retrieved_at
           OR sighting.available_at < sighting.source_published_at
           OR sighting.available_at > sighting.retrieved_at
           OR sighting.source_published_at > NEW.prediction_cutoff_at
           OR sighting.available_at > NEW.prediction_cutoff_at THEN
            RAISE EXCEPTION 'PRE_MATCH_SOURCE_NOT_AVAILABLE_AT_CUTOFF';
        END IF;
    ELSIF sighting.availability_basis = 'SYSTEM_OBSERVED_AT' THEN
        IF sighting.source_published_at IS NOT NULL
           OR sighting.system_observed_at IS NULL
           OR sighting.available_at <> sighting.system_observed_at
           OR sighting.system_observed_at > NEW.prediction_cutoff_at
           OR sighting.system_observed_at >= target_fixture.kickoff_at THEN
            RAISE EXCEPTION 'PRE_MATCH_SYSTEM_OBSERVATION_NOT_AVAILABLE_AT_CUTOFF';
        END IF;
    ELSE
        RAISE EXCEPTION 'PRE_MATCH_VERIFIED_AVAILABILITY_BASIS_REQUIRED';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM veltrix_ai_analyst.provider_responses r
        WHERE r.id = sighting.provider_response_id
          AND r.provider = observation.provider
          AND r.source_id = observation.source_id
          AND r.http_status BETWEEN 200 AND 299
          AND (
              sighting.availability_basis <> 'SYSTEM_OBSERVED_AT'
              OR (
                  r.fetched_at = sighting.retrieved_at
                  AND r.system_observed_at = sighting.system_observed_at
              )
          )
    ) THEN
        RAISE EXCEPTION 'PRE_MATCH_RESPONSE_PROVENANCE_INVALID';
    END IF;

    SELECT a.*
    INTO approval
    FROM veltrix_ai_analyst.source_approvals a
    WHERE a.approval_id = observation.rights_approval_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRE_MATCH_SOURCE_APPROVAL_NOT_FOUND';
    END IF;
    IF approval.status <> 'APPROVED'
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

    IF FOUND AND latest_approval_event.status <> 'APPROVED' THEN
        RAISE EXCEPTION 'PRE_MATCH_SOURCE_RIGHTS_REVOKED_AT_CUTOFF';
    END IF;

    RETURN NEW;
END;
$$;
