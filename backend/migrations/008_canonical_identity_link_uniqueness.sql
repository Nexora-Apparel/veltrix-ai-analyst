CREATE OR REPLACE FUNCTION veltrix_ai_analyst.enforce_canonical_link_provenance()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    observation RECORD;
    sighting RECORD;
    response RECORD;
    expected_entity_type TEXT;
    expected_entity_id TEXT;
    expected_data_type TEXT;
BEGIN
    IF TG_TABLE_NAME = 'provider_team_identity_links' THEN
        expected_entity_type := 'team';
        expected_entity_id := NEW.provider_team_id;
        expected_data_type := 'team_catalogue';
    ELSIF TG_TABLE_NAME = 'provider_competition_identity_links' THEN
        expected_entity_type := 'competition';
        expected_entity_id := NEW.provider_competition_id;
        expected_data_type := 'competition_catalogue';
    ELSIF TG_TABLE_NAME = 'canonical_fixture_sources' THEN
        expected_entity_type := 'fixture';
        expected_entity_id := NEW.provider_fixture_id;
        expected_data_type := 'fixtures_and_results';
    ELSE
        RAISE EXCEPTION 'CANONICAL_LINK_TABLE_NOT_SUPPORTED';
    END IF;

    SELECT provider, source_id, data_type, entity_type, provider_entity_id,
           payload_sha256, rights_approval_id
    INTO observation
    FROM veltrix_ai_analyst.source_observations
    WHERE id = NEW.source_observation_id;

    IF NOT FOUND
       OR observation.provider <> NEW.provider
       OR observation.source_id <> NEW.source_id
       OR observation.data_type <> expected_data_type
       OR observation.entity_type <> expected_entity_type
       OR observation.provider_entity_id <> expected_entity_id
       OR observation.payload_sha256 <> NEW.payload_sha256
       OR observation.rights_approval_id <> NEW.rights_approval_id THEN
        RAISE EXCEPTION 'CANONICAL_SOURCE_OBSERVATION_MISMATCH';
    END IF;

    SELECT source_observation_id, provider_response_id, payload_sha256
    INTO sighting
    FROM veltrix_ai_analyst.source_observation_sightings
    WHERE id = NEW.source_sighting_id;

    IF NOT FOUND
       OR sighting.source_observation_id <> NEW.source_observation_id
       OR sighting.provider_response_id <> NEW.provider_response_id
       OR sighting.payload_sha256 <> NEW.payload_sha256 THEN
        RAISE EXCEPTION 'CANONICAL_SOURCE_SIGHTING_MISMATCH';
    END IF;

    SELECT provider, source_id, http_status, rights_approval_id
    INTO response
    FROM veltrix_ai_analyst.provider_responses
    WHERE id = NEW.provider_response_id;

    IF NOT FOUND
       OR response.provider <> observation.provider
       OR response.source_id <> observation.source_id
       OR response.provider <> NEW.provider
       OR response.source_id <> NEW.source_id
       OR response.http_status NOT BETWEEN 200 AND 299
       OR response.rights_approval_id <> NEW.rights_approval_id THEN
        RAISE EXCEPTION 'CANONICAL_SOURCE_RESPONSE_OR_RIGHTS_MISMATCH';
    END IF;

    -- NEW is a trigger-specific RECORD. Keep fixture-only field references
    -- inside this branch so team/competition inserts never resolve them.
    IF TG_TABLE_NAME = 'canonical_fixture_sources' THEN
        IF NOT EXISTS (
            SELECT 1
            FROM veltrix_ai_analyst.provider_fixtures pf
            JOIN veltrix_ai_analyst.canonical_fixtures cf
              ON cf.id = NEW.canonical_fixture_id
            WHERE pf.id = NEW.provider_fixture_row_id
              AND pf.kickoff_at = cf.kickoff_at
              AND pf.status = cf.status
              AND pf.home_goals IS NOT DISTINCT FROM cf.home_goals
              AND pf.away_goals IS NOT DISTINCT FROM cf.away_goals
        ) THEN
            RAISE EXCEPTION 'CANONICAL_FIXTURE_SOURCE_FACTS_MISMATCH';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- Enforce one canonical source-local identity link per provider identity.
-- These unique indexes make the materializer idempotent under concurrent runs.
CREATE UNIQUE INDEX provider_team_identity_links_source_identity_uk
    ON veltrix_ai_analyst.provider_team_identity_links(provider, source_id, provider_team_id);

CREATE UNIQUE INDEX provider_competition_identity_links_source_identity_uk
    ON veltrix_ai_analyst.provider_competition_identity_links(
        provider, source_id, provider_competition_id
    );
