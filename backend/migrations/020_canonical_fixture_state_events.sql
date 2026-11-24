-- Canonical fixture current-state projection backed by append-only PIT source events.
-- The provider fixture projection is mutable; its source observations are immutable.
-- Keep the source identity link separate from the latest schedule/result state evidence.

CREATE TABLE veltrix_ai_analyst.canonical_fixture_state_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    canonical_fixture_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_fixtures(id) ON DELETE RESTRICT,
    fixture_source_link_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_fixture_sources(id) ON DELETE RESTRICT,
    provider_fixture_row_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.provider_fixtures(id) ON DELETE RESTRICT,
    source_observation_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observations(id) ON DELETE RESTRICT,
    source_sighting_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observation_sightings(id) ON DELETE RESTRICT,
    provider_response_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT,
    rights_approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    payload_sha256 CHAR(64) NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    response_sha256 CHAR(64) NOT NULL CHECK (response_sha256 ~ '^[0-9a-f]{64}$'),
    observed_at TIMESTAMPTZ NOT NULL,
    kickoff_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('SCHEDULED', 'LIVE', 'FINISHED', 'POSTPONED', 'CANCELLED', 'ABANDONED', 'UNKNOWN')
    ),
    home_goals SMALLINT CHECK (home_goals IS NULL OR home_goals >= 0),
    away_goals SMALLINT CHECK (away_goals IS NULL OR away_goals >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (fixture_source_link_id, source_observation_id, source_sighting_id),
    CHECK (
        (home_goals IS NULL AND away_goals IS NULL)
        OR
        (home_goals IS NOT NULL AND away_goals IS NOT NULL)
    )
);

CREATE INDEX canonical_fixture_state_events_latest_idx
    ON veltrix_ai_analyst.canonical_fixture_state_events (
        canonical_fixture_id, observed_at DESC, id DESC
    );

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.enforce_canonical_fixture_state_event()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    link RECORD;
    canonical RECORD;
    observation RECORD;
    sighting RECORD;
    response RECORD;
    approval RECORD;
    effective_approval_status TEXT;
    payload_home_goals INTEGER;
    payload_away_goals INTEGER;
BEGIN
    SELECT source_link.id,
           source_link.provider_fixture_row_id,
           source_link.canonical_fixture_id,
           source_link.provider,
           source_link.source_id,
           source_link.provider_fixture_id,
           source_link.mapping_method,
           provider_fixture.provider_fixture_id AS provider_fixture_row_fixture_id,
           provider_fixture.provider_competition_id,
           provider_fixture.home_team_provider_id,
           provider_fixture.away_team_provider_id,
           provider_fixture.kickoff_at AS provider_kickoff_at,
           provider_fixture.status AS provider_status,
           provider_fixture.home_goals AS provider_home_goals,
           provider_fixture.away_goals AS provider_away_goals
    INTO link
    FROM veltrix_ai_analyst.canonical_fixture_sources source_link
    JOIN veltrix_ai_analyst.provider_fixtures provider_fixture
      ON provider_fixture.id = source_link.provider_fixture_row_id
    WHERE source_link.id = NEW.fixture_source_link_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_SOURCE_LINK_MISSING';
    END IF;
    IF link.provider_fixture_row_id <> NEW.provider_fixture_row_id
       OR link.canonical_fixture_id <> NEW.canonical_fixture_id
       OR link.mapping_method <> 'EXACT_PROVIDER_FIXTURE_ID'
       OR link.provider_fixture_id <> link.provider_fixture_row_fixture_id THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_SOURCE_LINK_MISMATCH';
    END IF;

    IF (
        SELECT COUNT(*)
        FROM veltrix_ai_analyst.canonical_fixture_sources source_link
        WHERE source_link.canonical_fixture_id = NEW.canonical_fixture_id
    ) <> 1 THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_CROSS_SOURCE_LINK_NOT_ALLOWED';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM veltrix_ai_analyst.effective_canonical_fixture_sources effective_link
        WHERE effective_link.id = NEW.fixture_source_link_id
          AND effective_link.effective_mapping_status = 'SOURCE_FIXTURE_LINK_REVIEWED'
    ) THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_SOURCE_LINK_NOT_REVIEWED';
    END IF;

    SELECT *
    INTO canonical
    FROM veltrix_ai_analyst.canonical_fixtures
    WHERE id = NEW.canonical_fixture_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_CANONICAL_FIXTURE_MISSING';
    END IF;
    IF canonical.identity_status <> 'VERIFIED'
       OR canonical.kickoff_at <> NEW.kickoff_at THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_IDENTITY_NOT_VERIFIED';
    END IF;

    IF NEW.kickoff_at <> link.provider_kickoff_at
       OR NEW.status <> link.provider_status
       OR NEW.home_goals IS DISTINCT FROM link.provider_home_goals
       OR NEW.away_goals IS DISTINCT FROM link.provider_away_goals THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_NOT_CURRENT_PROVIDER_PROJECTION';
    END IF;

    SELECT *
    INTO observation
    FROM veltrix_ai_analyst.source_observations
    WHERE id = NEW.source_observation_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_OBSERVATION_MISSING';
    END IF;
    IF observation.provider <> link.provider
       OR observation.source_id <> link.source_id
       OR observation.data_type <> 'fixtures_and_results'
       OR observation.entity_type <> 'fixture'
       OR observation.provider_entity_id <> link.provider_fixture_id
       OR observation.payload_sha256 <> NEW.payload_sha256
       OR observation.rights_approval_id <> NEW.rights_approval_id THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_OBSERVATION_MISMATCH';
    END IF;

    payload_home_goals := CASE
        WHEN jsonb_typeof(observation.payload->'home_goals') = 'number'
            THEN (observation.payload->>'home_goals')::integer
        ELSE NULL
    END;
    payload_away_goals := CASE
        WHEN jsonb_typeof(observation.payload->'away_goals') = 'number'
            THEN (observation.payload->>'away_goals')::integer
        ELSE NULL
    END;

    IF lower(COALESCE(observation.payload->>'status', '')) <> lower(NEW.status)
       OR NULLIF(observation.payload->>'kickoff_at', '')::timestamptz IS DISTINCT FROM NEW.kickoff_at
       OR observation.payload->>'competition_id' IS DISTINCT FROM link.provider_competition_id
       OR observation.payload->>'home_team_id' IS DISTINCT FROM link.home_team_provider_id
       OR observation.payload->>'away_team_id' IS DISTINCT FROM link.away_team_provider_id
       OR observation.payload #>> '{provenance,provider_record_id}' IS DISTINCT FROM link.provider_fixture_id
       OR payload_home_goals IS DISTINCT FROM NEW.home_goals
       OR payload_away_goals IS DISTINCT FROM NEW.away_goals THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_PAYLOAD_FACTS_MISMATCH';
    END IF;

    SELECT *
    INTO sighting
    FROM veltrix_ai_analyst.source_observation_sightings
    WHERE id = NEW.source_sighting_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_SIGHTING_MISSING';
    END IF;
    IF sighting.source_observation_id <> NEW.source_observation_id
       OR sighting.provider_response_id <> NEW.provider_response_id
       OR sighting.payload_sha256 <> NEW.payload_sha256
       OR sighting.availability_basis <> 'SYSTEM_OBSERVED_AT'
       OR sighting.point_in_time_certifiable IS NOT TRUE
       OR sighting.system_observed_at IS NULL
       OR sighting.available_at IS DISTINCT FROM sighting.system_observed_at
       OR sighting.system_observed_at < sighting.retrieved_at
       OR sighting.source_published_at IS NOT NULL
       OR NEW.observed_at <> sighting.system_observed_at THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_SIGHTING_NOT_PIT_CERTIFIABLE';
    END IF;

    SELECT *
    INTO response
    FROM veltrix_ai_analyst.provider_responses
    WHERE id = NEW.provider_response_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_RESPONSE_MISSING';
    END IF;
    IF response.provider <> link.provider
       OR response.source_id <> link.source_id
       OR response.rights_approval_id <> NEW.rights_approval_id
       OR response.http_status NOT BETWEEN 200 AND 299
       OR response.fetched_at <> sighting.retrieved_at
       OR response.system_observed_at IS DISTINCT FROM sighting.system_observed_at
       OR response.response_sha256 <> NEW.response_sha256 THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_RESPONSE_PROVENANCE_MISMATCH';
    END IF;

    SELECT *
    INTO approval
    FROM veltrix_ai_analyst.source_approvals
    WHERE approval_id = NEW.rights_approval_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_APPROVAL_MISSING';
    END IF;
    IF approval.provider <> link.provider
       OR approval.source_id <> link.source_id
       OR approval.scope_type IS DISTINCT FROM 'competition_id'
       OR NOT COALESCE(
           approval.scope_values @> jsonb_build_array(link.provider_competition_id),
           FALSE
       )
       OR approval.valid_from > NEW.observed_at
       OR (approval.valid_until IS NOT NULL AND approval.valid_until <= NEW.observed_at)
       OR NOT COALESCE(
           approval.permitted_uses @> '["STORAGE", "INTERNAL_ANALYSIS", "FEATURE_ENGINEERING", "MODEL_TRAINING", "MODEL_VALIDATION"]'::jsonb,
           FALSE
       ) THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_SOURCE_RIGHTS_INVALID';
    END IF;

    SELECT COALESCE(
        (
            SELECT event.status
            FROM veltrix_ai_analyst.source_approval_status_events event
            WHERE event.approval_id = approval.approval_id
              AND event.effective_at <= NEW.observed_at
            ORDER BY event.effective_at DESC, event.id DESC
            LIMIT 1
        ),
        approval.status
    )
    INTO effective_approval_status;

    IF effective_approval_status IS DISTINCT FROM 'APPROVED' THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_SOURCE_APPROVAL_NOT_ACTIVE';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM veltrix_ai_analyst.effective_provider_competition_identity_links competition_link
        WHERE competition_link.provider = link.provider
          AND competition_link.source_id = link.source_id
          AND competition_link.provider_competition_id = link.provider_competition_id
          AND competition_link.canonical_competition_id = canonical.canonical_competition_id
          AND competition_link.effective_mapping_status IN (
              'SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED'
          )
    ) OR NOT EXISTS (
        SELECT 1
        FROM veltrix_ai_analyst.effective_provider_team_identity_links team_link
        WHERE team_link.provider = link.provider
          AND team_link.source_id = link.source_id
          AND team_link.provider_team_id = link.home_team_provider_id
          AND team_link.canonical_team_id = canonical.home_canonical_team_id
          AND team_link.effective_mapping_status IN (
              'SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED'
          )
    ) OR NOT EXISTS (
        SELECT 1
        FROM veltrix_ai_analyst.effective_provider_team_identity_links team_link
        WHERE team_link.provider = link.provider
          AND team_link.source_id = link.source_id
          AND team_link.provider_team_id = link.away_team_provider_id
          AND team_link.canonical_team_id = canonical.away_canonical_team_id
          AND team_link.effective_mapping_status IN (
              'SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED'
          )
    ) THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_CANONICAL_MAPPINGS_NOT_REVIEWED';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM veltrix_ai_analyst.source_observations newer_observation
        LEFT JOIN LATERAL (
            SELECT candidate.*
            FROM veltrix_ai_analyst.source_observation_sightings candidate
            WHERE candidate.source_observation_id = newer_observation.id
            ORDER BY
                COALESCE(candidate.system_observed_at, candidate.retrieved_at) DESC,
                candidate.id DESC
            LIMIT 1
        ) newer_sighting ON TRUE
        WHERE newer_observation.provider = link.provider
          AND newer_observation.source_id = link.source_id
          AND newer_observation.data_type = 'fixtures_and_results'
          AND newer_observation.entity_type = 'fixture'
          AND newer_observation.provider_entity_id = link.provider_fixture_id
          AND (
              COALESCE(
                  newer_sighting.system_observed_at,
                  newer_sighting.retrieved_at,
                  newer_observation.retrieved_at
              ),
              COALESCE(newer_sighting.id, 0),
              newer_observation.id
          ) > (
              NEW.observed_at,
              NEW.source_sighting_id,
              NEW.source_observation_id
          )
    ) THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_EVENT_NOT_LATEST_SOURCE_OBSERVATION';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM veltrix_ai_analyst.canonical_fixture_state_events existing
        WHERE existing.canonical_fixture_id = NEW.canonical_fixture_id
          AND existing.observed_at >= NEW.observed_at
    ) THEN
        RAISE EXCEPTION 'CANONICAL_FIXTURE_STATE_EVENT_NOT_MONOTONIC';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER canonical_fixture_state_event_provenance_guard
    BEFORE INSERT ON veltrix_ai_analyst.canonical_fixture_state_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.enforce_canonical_fixture_state_event();

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.apply_canonical_fixture_state_event()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM veltrix_ai_analyst.canonical_fixture_state_events later
        WHERE later.canonical_fixture_id = NEW.canonical_fixture_id
          AND (later.observed_at, later.id) > (NEW.observed_at, NEW.id)
    ) THEN
        UPDATE veltrix_ai_analyst.canonical_fixtures
        SET status = NEW.status,
            home_goals = NEW.home_goals,
            away_goals = NEW.away_goals
        WHERE id = NEW.canonical_fixture_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER canonical_fixture_state_projection
    AFTER INSERT ON veltrix_ai_analyst.canonical_fixture_state_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.apply_canonical_fixture_state_event();

CREATE TRIGGER canonical_fixture_state_events_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.canonical_fixture_state_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE VIEW veltrix_ai_analyst.latest_canonical_fixture_states AS
SELECT DISTINCT ON (state_event.canonical_fixture_id)
       state_event.*
FROM veltrix_ai_analyst.canonical_fixture_state_events state_event
ORDER BY state_event.canonical_fixture_id, state_event.observed_at DESC, state_event.id DESC;

CREATE VIEW veltrix_ai_analyst.canonical_fixture_state_provenance_audit AS
SELECT
    link.id AS fixture_source_link_id,
    canonical.id AS canonical_fixture_id,
    fixture.id AS provider_fixture_row_id,
    state.id AS state_event_id,
    state.source_observation_id,
    state.source_sighting_id,
    state.provider_response_id,
    state.observed_at,
    CASE
        WHEN state.id IS NOT NULL
         AND state.fixture_source_link_id = link.id
         AND state.provider_fixture_row_id = fixture.id
         AND state.source_observation_id = latest_source.observation_id
         AND state.source_sighting_id = latest_source.sighting_id
         AND state.provider_response_id = latest_source.provider_response_id
         AND state.kickoff_at = fixture.kickoff_at
         AND state.status = fixture.status
         AND state.home_goals IS NOT DISTINCT FROM fixture.home_goals
         AND state.away_goals IS NOT DISTINCT FROM fixture.away_goals
         AND canonical.status = fixture.status
         AND canonical.home_goals IS NOT DISTINCT FROM fixture.home_goals
         AND canonical.away_goals IS NOT DISTINCT FROM fixture.away_goals
         AND canonical.identity_status = 'VERIFIED'
         AND effective_link.effective_mapping_status = 'SOURCE_FIXTURE_LINK_REVIEWED'
        THEN 'STATE_PROVENANCE_VERIFIED'
        ELSE 'STATE_PROVENANCE_INVALID'
    END AS state_provenance_status
FROM veltrix_ai_analyst.canonical_fixture_sources link
JOIN veltrix_ai_analyst.provider_fixtures fixture
  ON fixture.id = link.provider_fixture_row_id
JOIN veltrix_ai_analyst.canonical_fixtures canonical
  ON canonical.id = link.canonical_fixture_id
LEFT JOIN veltrix_ai_analyst.effective_canonical_fixture_sources effective_link
  ON effective_link.id = link.id
LEFT JOIN veltrix_ai_analyst.latest_canonical_fixture_states state
  ON state.canonical_fixture_id = canonical.id
LEFT JOIN LATERAL (
    SELECT
        observation.id AS observation_id,
        sighting.id AS sighting_id,
        sighting.provider_response_id
    FROM veltrix_ai_analyst.source_observations observation
    LEFT JOIN LATERAL (
        SELECT candidate.*
        FROM veltrix_ai_analyst.source_observation_sightings candidate
        WHERE candidate.source_observation_id = observation.id
        ORDER BY
            COALESCE(candidate.system_observed_at, candidate.retrieved_at) DESC,
            candidate.id DESC
        LIMIT 1
    ) sighting ON TRUE
    WHERE observation.provider = fixture.provider
      AND observation.source_id = fixture.source_id
      AND observation.data_type = 'fixtures_and_results'
      AND observation.entity_type = 'fixture'
      AND observation.provider_entity_id = fixture.provider_fixture_id
    ORDER BY
        COALESCE(sighting.system_observed_at, sighting.retrieved_at, observation.retrieved_at) DESC,
        sighting.id DESC NULLS LAST,
        observation.id DESC
    LIMIT 1
) latest_source ON TRUE;
