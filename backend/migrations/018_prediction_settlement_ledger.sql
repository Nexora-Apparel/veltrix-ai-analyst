-- Append-only, source-provenance-backed settlements for predictions that were published.
-- A later corrected source result is a new event; prior settlement evidence is never rewritten.

CREATE TABLE veltrix_ai_analyst.prediction_settlement_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    prediction_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.predictions(prediction_id) ON DELETE RESTRICT,
    source_observation_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observations(id) ON DELETE RESTRICT,
    source_sighting_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observation_sightings(id) ON DELETE RESTRICT,
    provider_response_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT,
    rights_approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    home_goals SMALLINT NOT NULL CHECK (home_goals >= 0),
    away_goals SMALLINT NOT NULL CHECK (away_goals >= 0),
    settled_at TIMESTAMPTZ NOT NULL,
    source_payload_sha256 CHAR(64) NOT NULL
        CHECK (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    provider_response_sha256 CHAR(64) NOT NULL
        CHECK (provider_response_sha256 ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT statement_timestamp(),
    UNIQUE (prediction_id, source_observation_id)
);

CREATE INDEX prediction_settlement_events_latest_idx
    ON veltrix_ai_analyst.prediction_settlement_events
       (prediction_id, settled_at DESC, id DESC);

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.enforce_prediction_settlement_evidence()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    prediction_fixture_id UUID;
    fixture_kickoff TIMESTAMPTZ;
    fixture_identity_status TEXT;
    fixture_completeness_status TEXT;
    latest_publication_decision TEXT;
    latest_settlement_at TIMESTAMPTZ;
    evidence RECORD;
BEGIN
    SELECT prediction.canonical_fixture_id, fixture.kickoff_at,
           fixture.identity_status, fixture.completeness_status
    INTO prediction_fixture_id, fixture_kickoff,
         fixture_identity_status, fixture_completeness_status
    FROM veltrix_ai_analyst.predictions prediction
    JOIN veltrix_ai_analyst.canonical_fixtures fixture
      ON fixture.id = prediction.canonical_fixture_id
    WHERE prediction.prediction_id = NEW.prediction_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PREDICTION_SETTLEMENT_PREDICTION_NOT_FOUND';
    END IF;

    IF fixture_identity_status <> 'VERIFIED'
       OR fixture_completeness_status <> 'RECONCILED' THEN
        RAISE EXCEPTION 'PREDICTION_SETTLEMENT_FIXTURE_NOT_RECONCILED';
    END IF;

    SELECT decision INTO latest_publication_decision
    FROM veltrix_ai_analyst.prediction_publication_events
    WHERE prediction_id = NEW.prediction_id
    ORDER BY effective_at DESC, id DESC
    LIMIT 1;

    IF latest_publication_decision IS DISTINCT FROM 'PUBLISHED' THEN
        RAISE EXCEPTION 'PREDICTION_SETTLEMENT_REQUIRES_CURRENT_PUBLICATION';
    END IF;

    IF NEW.settled_at <= fixture_kickoff
       OR NEW.settled_at > clock_timestamp() THEN
        RAISE EXCEPTION 'PREDICTION_SETTLEMENT_TIME_OUTSIDE_VALID_WINDOW';
    END IF;

    SELECT
        provider_fixture.provider_fixture_id,
        provider_fixture.status AS provider_fixture_status,
        provider_fixture.home_goals AS provider_fixture_home_goals,
        provider_fixture.away_goals AS provider_fixture_away_goals,
        provider_fixture.kickoff_at AS provider_fixture_kickoff,
        observation.provider AS observation_provider,
        observation.source_id AS observation_source_id,
        observation.data_type,
        observation.entity_type,
        observation.provider_entity_id,
        observation.payload,
        observation.payload_sha256,
        observation.rights_approval_id AS observation_rights_approval_id,
        observation.availability_basis AS observation_availability_basis,
        observation.point_in_time_certifiable AS observation_pit_certifiable,
        observation.retrieved_at AS observation_retrieved_at,
        observation.system_observed_at AS observation_system_observed_at,
        sighting.source_observation_id AS sighting_observation_id,
        sighting.provider_response_id AS sighting_response_id,
        sighting.retrieved_at AS sighting_retrieved_at,
        sighting.system_observed_at AS sighting_system_observed_at,
        sighting.availability_basis AS sighting_availability_basis,
        sighting.point_in_time_certifiable AS sighting_pit_certifiable,
        sighting.payload_sha256 AS sighting_payload_sha256,
        response.provider AS response_provider,
        response.source_id AS response_source_id,
        response.http_status,
        response.fetched_at,
        response.system_observed_at AS response_system_observed_at,
        response.response_sha256,
        response.rights_approval_id AS response_rights_approval_id,
        approval.provider AS approval_provider,
        approval.source_id AS approval_source_id,
        approval.status AS approval_status,
        approval.scope_values,
        approval.data_types,
        approval.permitted_uses,
        approval.valid_from,
        approval.valid_until,
        COALESCE(approval_event.status, approval.status) AS effective_approval_status,
        fixture_source_review.decision AS fixture_source_review_decision
    INTO evidence
    FROM veltrix_ai_analyst.canonical_fixture_sources fixture_source
    JOIN veltrix_ai_analyst.provider_fixtures provider_fixture
      ON provider_fixture.id = fixture_source.provider_fixture_row_id
     AND provider_fixture.provider = fixture_source.provider
     AND provider_fixture.source_id = fixture_source.source_id
     AND provider_fixture.provider_fixture_id = fixture_source.provider_fixture_id
    JOIN veltrix_ai_analyst.source_observations observation
      ON observation.id = NEW.source_observation_id
     AND observation.provider = provider_fixture.provider
     AND observation.source_id = provider_fixture.source_id
     AND observation.provider_entity_id = provider_fixture.provider_fixture_id
    JOIN veltrix_ai_analyst.source_observation_sightings sighting
      ON sighting.id = NEW.source_sighting_id
     AND sighting.source_observation_id = observation.id
    JOIN veltrix_ai_analyst.provider_responses response
      ON response.id = NEW.provider_response_id
     AND response.id = sighting.provider_response_id
    JOIN veltrix_ai_analyst.source_approvals approval
      ON approval.approval_id = observation.rights_approval_id
     AND approval.approval_id = response.rights_approval_id
     AND approval.approval_id = NEW.rights_approval_id
    LEFT JOIN LATERAL (
        SELECT event.status
        FROM veltrix_ai_analyst.source_approval_status_events event
        WHERE event.approval_id = approval.approval_id
          AND event.effective_at <= NEW.settled_at
        ORDER BY event.effective_at DESC, event.id DESC
        LIMIT 1
    ) approval_event ON TRUE
    LEFT JOIN LATERAL (
        SELECT event.decision
        FROM veltrix_ai_analyst.canonical_identity_review_events event
        WHERE event.fixture_source_link_id = fixture_source.id
        ORDER BY event.reviewed_at DESC, event.id DESC
        LIMIT 1
    ) fixture_source_review ON TRUE
    WHERE fixture_source.canonical_fixture_id = prediction_fixture_id
      AND fixture_source.mapping_status = 'REVIEW_REQUIRED'
      AND fixture_source_review.decision = 'SOURCE_FIXTURE_LINK_REVIEWED';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PREDICTION_SETTLEMENT_SOURCE_LINK_NOT_VERIFIED';
    END IF;

    IF evidence.observation_provider <> '5DollarFootballAPI'
       OR evidence.observation_source_id <> '5dollarfootballapi'
       OR evidence.data_type <> 'fixtures_and_results'
       OR evidence.entity_type <> 'fixture'
       OR evidence.observation_availability_basis <> 'SYSTEM_OBSERVED_AT'
       OR evidence.observation_pit_certifiable IS NOT TRUE
       OR evidence.observation_system_observed_at IS DISTINCT FROM NEW.settled_at
       OR evidence.observation_retrieved_at > NEW.settled_at
       OR evidence.sighting_observation_id <> NEW.source_observation_id
       OR evidence.sighting_response_id <> NEW.provider_response_id
       OR evidence.sighting_availability_basis <> 'SYSTEM_OBSERVED_AT'
       OR evidence.sighting_pit_certifiable IS NOT TRUE
       OR evidence.sighting_system_observed_at IS DISTINCT FROM NEW.settled_at
       OR evidence.sighting_retrieved_at > NEW.settled_at
       OR evidence.sighting_payload_sha256 <> evidence.payload_sha256
       OR evidence.response_provider <> evidence.observation_provider
       OR evidence.response_source_id <> evidence.observation_source_id
       OR evidence.http_status NOT BETWEEN 200 AND 299
       OR evidence.fetched_at <> evidence.sighting_retrieved_at
       OR evidence.response_system_observed_at IS DISTINCT FROM NEW.settled_at
       OR evidence.response_sha256 <> NEW.provider_response_sha256
       OR evidence.payload_sha256 <> NEW.source_payload_sha256
       OR evidence.approval_provider <> evidence.observation_provider
       OR evidence.approval_source_id <> evidence.observation_source_id
       OR evidence.approval_status <> 'APPROVED'
       OR evidence.effective_approval_status <> 'APPROVED'
       OR evidence.valid_from > NEW.settled_at
       OR (evidence.valid_until IS NOT NULL AND evidence.valid_until <= NEW.settled_at)
       OR NOT (evidence.data_types @> '["fixtures_and_results"]'::jsonb)
       OR NOT (evidence.permitted_uses @> '["MODEL_TRAINING","MODEL_VALIDATION"]'::jsonb)
       OR NOT (evidence.scope_values @> jsonb_build_array(
            (SELECT provider_competition_id
             FROM veltrix_ai_analyst.provider_fixtures
             WHERE id = (
                 SELECT provider_fixture_row_id
                 FROM veltrix_ai_analyst.canonical_fixture_sources
                 WHERE canonical_fixture_id = prediction_fixture_id
                   AND provider_fixture_id = evidence.provider_fixture_id
                 LIMIT 1
             ))
       ))
       OR evidence.provider_fixture_status <> 'FINISHED'
       OR evidence.provider_fixture_home_goals IS DISTINCT FROM NEW.home_goals
       OR evidence.provider_fixture_away_goals IS DISTINCT FROM NEW.away_goals
       OR evidence.provider_fixture_kickoff IS DISTINCT FROM fixture_kickoff
       OR lower(evidence.payload->>'status') <> 'finished'
       OR jsonb_typeof(evidence.payload->'home_goals') <> 'number'
       OR jsonb_typeof(evidence.payload->'away_goals') <> 'number'
       OR (evidence.payload->>'home_goals')::integer <> NEW.home_goals
       OR (evidence.payload->>'away_goals')::integer <> NEW.away_goals
       OR evidence.payload->>'competition_id' IS NULL
       OR evidence.payload->>'home_team_id' IS NULL
       OR evidence.payload->>'away_team_id' IS NULL
       OR evidence.payload->>'kickoff_at' IS NULL
       OR evidence.payload->>'competition_id' <> (
            SELECT provider_competition_id
            FROM veltrix_ai_analyst.provider_fixtures
            WHERE provider_fixture_id = evidence.provider_fixture_id
              AND provider = evidence.observation_provider
              AND source_id = evidence.observation_source_id
       )
       OR evidence.payload->>'home_team_id' <> (
            SELECT home_team_provider_id
            FROM veltrix_ai_analyst.provider_fixtures
            WHERE provider_fixture_id = evidence.provider_fixture_id
              AND provider = evidence.observation_provider
              AND source_id = evidence.observation_source_id
       )
       OR evidence.payload->>'away_team_id' <> (
            SELECT away_team_provider_id
            FROM veltrix_ai_analyst.provider_fixtures
            WHERE provider_fixture_id = evidence.provider_fixture_id
              AND provider = evidence.observation_provider
              AND source_id = evidence.observation_source_id
       )
       OR (evidence.payload->>'kickoff_at')::timestamptz <> fixture_kickoff
       OR evidence.payload #>> '{provenance,provider_record_id}' <> evidence.provider_fixture_id THEN
        RAISE EXCEPTION 'PREDICTION_SETTLEMENT_SOURCE_EVIDENCE_INVALID';
    END IF;

    SELECT settled_at INTO latest_settlement_at
    FROM veltrix_ai_analyst.prediction_settlement_events
    WHERE prediction_id = NEW.prediction_id
    ORDER BY settled_at DESC, id DESC
    LIMIT 1;

    IF latest_settlement_at IS NOT NULL AND NEW.settled_at <= latest_settlement_at THEN
        RAISE EXCEPTION 'PREDICTION_SETTLEMENT_TIME_NOT_MONOTONIC';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prediction_settlement_evidence_guard
    BEFORE INSERT ON veltrix_ai_analyst.prediction_settlement_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.enforce_prediction_settlement_evidence();

CREATE TRIGGER prediction_settlement_events_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.prediction_settlement_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE VIEW veltrix_ai_analyst.latest_prediction_settlements AS
SELECT DISTINCT ON (prediction_id)
       id, prediction_id, source_observation_id, source_sighting_id,
       provider_response_id, rights_approval_id, home_goals, away_goals,
       settled_at, source_payload_sha256, provider_response_sha256
FROM veltrix_ai_analyst.prediction_settlement_events
ORDER BY prediction_id, settled_at DESC, id DESC;
