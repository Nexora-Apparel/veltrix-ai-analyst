-- VELTRIX AI ANALYST: provenance-preserving canonical entity layer.
-- This migration creates schema only. It does not materialize or merge source rows.
-- Canonical identity, source rights and pre-match PIT eligibility remain separate gates.

ALTER TABLE veltrix_ai_analyst.provider_teams
    ADD CONSTRAINT provider_teams_canonical_provenance_uk
    UNIQUE (provider, source_id, provider_team_id, source_observation_id, rights_approval_id);

ALTER TABLE veltrix_ai_analyst.provider_competitions
    ADD CONSTRAINT provider_competitions_canonical_provenance_uk
    UNIQUE (
        provider, source_id, provider_competition_id, source_observation_id, rights_approval_id
    );

ALTER TABLE veltrix_ai_analyst.provider_fixtures
    ADD CONSTRAINT provider_fixtures_canonical_provenance_uk
    UNIQUE (
        id, provider, source_id, provider_fixture_id, source_observation_id, rights_approval_id
    );

CREATE TABLE veltrix_ai_analyst.canonical_teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name TEXT NOT NULL CHECK (length(btrim(display_name)) BETWEEN 1 AND 200),
    country_code TEXT CHECK (country_code IS NULL OR country_code ~ '^[A-Z]{2}$'),
    association TEXT,
    identity_basis TEXT NOT NULL DEFAULT 'SOURCE_LOCAL_ONLY'
        CHECK (identity_basis IN ('SOURCE_LOCAL_ONLY', 'REAL_WORLD_VERIFIED', 'UNRESOLVED')),
    lifecycle_status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (lifecycle_status IN ('ACTIVE', 'INACTIVE', 'RETIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE veltrix_ai_analyst.canonical_competitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name TEXT NOT NULL CHECK (length(btrim(display_name)) BETWEEN 1 AND 200),
    country_code TEXT CHECK (country_code IS NULL OR country_code ~ '^[A-Z]{2}$'),
    association TEXT,
    competition_level TEXT,
    season_model TEXT,
    identity_basis TEXT NOT NULL DEFAULT 'SOURCE_LOCAL_ONLY'
        CHECK (identity_basis IN ('SOURCE_LOCAL_ONLY', 'REAL_WORLD_VERIFIED', 'UNRESOLVED')),
    lifecycle_status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (lifecycle_status IN ('ACTIVE', 'INACTIVE', 'RETIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE veltrix_ai_analyst.canonical_fixtures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_competition_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_competitions(id) ON DELETE RESTRICT,
    home_canonical_team_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_teams(id) ON DELETE RESTRICT,
    away_canonical_team_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_teams(id) ON DELETE RESTRICT,
    kickoff_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('SCHEDULED', 'LIVE', 'FINISHED', 'POSTPONED', 'CANCELLED', 'ABANDONED', 'UNKNOWN')
    ),
    home_goals SMALLINT CHECK (home_goals IS NULL OR home_goals >= 0),
    away_goals SMALLINT CHECK (away_goals IS NULL OR away_goals >= 0),
    identity_status TEXT NOT NULL DEFAULT 'IDENTITY_REVIEW_REQUIRED'
        CHECK (identity_status IN ('IDENTITY_REVIEW_REQUIRED', 'VERIFIED', 'CONFLICT')),
    completeness_status TEXT NOT NULL DEFAULT 'SOURCE_ROW_ONLY'
        CHECK (completeness_status IN ('SOURCE_ROW_ONLY', 'RECONCILED', 'INCOMPLETE', 'CONFLICT')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (home_canonical_team_id <> away_canonical_team_id),
    CHECK (
        (status = 'FINISHED' AND home_goals IS NOT NULL AND away_goals IS NOT NULL)
        OR
        (status <> 'FINISHED' AND home_goals IS NULL AND away_goals IS NULL)
    )
);
CREATE INDEX canonical_fixtures_competition_kickoff_idx
    ON veltrix_ai_analyst.canonical_fixtures(canonical_competition_id, kickoff_at);
CREATE INDEX canonical_fixtures_identity_status_idx
    ON veltrix_ai_analyst.canonical_fixtures(identity_status, completeness_status);

CREATE TABLE veltrix_ai_analyst.provider_team_identity_links (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    provider_team_id TEXT NOT NULL,
    canonical_team_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_teams(id) ON DELETE RESTRICT,
    source_observation_id BIGINT NOT NULL,
    source_sighting_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observation_sightings(id) ON DELETE RESTRICT,
    provider_response_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT,
    rights_approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    payload_sha256 CHAR(64) NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    mapping_method TEXT NOT NULL CHECK (
        mapping_method IN ('EXACT_PROVIDER_ID', 'MANUAL_EVIDENCE')
    ),
    mapping_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED'
        CHECK (
            mapping_status IN (
                'SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED',
                'REVIEW_REQUIRED', 'CONFLICT', 'REJECTED'
            )
        ),
    evidence_uri TEXT,
    evidence_sha256 CHAR(64) CHECK (
        evidence_sha256 IS NULL OR evidence_sha256 ~ '^[0-9a-f]{64}$'
    ),
    reviewer_id TEXT,
    reviewed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (
        provider, source_id, provider_team_id, source_observation_id, rights_approval_id
    ) REFERENCES veltrix_ai_analyst.provider_teams (
        provider, source_id, provider_team_id, source_observation_id, rights_approval_id
    ) ON DELETE RESTRICT,
    CHECK (
        (reviewer_id IS NULL AND reviewed_at IS NULL)
        OR
        (reviewer_id IS NOT NULL AND length(btrim(reviewer_id)) > 0 AND reviewed_at IS NOT NULL)
    ),
    CHECK (
        mapping_status NOT IN ('SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED')
        OR (
            reviewer_id IS NOT NULL AND evidence_uri IS NOT NULL AND evidence_uri <> ''
            AND evidence_sha256 IS NOT NULL
        )
    )
);
CREATE INDEX provider_team_identity_links_canonical_idx
    ON veltrix_ai_analyst.provider_team_identity_links(canonical_team_id);

CREATE TABLE veltrix_ai_analyst.provider_competition_identity_links (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    provider_competition_id TEXT NOT NULL,
    canonical_competition_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_competitions(id) ON DELETE RESTRICT,
    source_observation_id BIGINT NOT NULL,
    source_sighting_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observation_sightings(id) ON DELETE RESTRICT,
    provider_response_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT,
    rights_approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    payload_sha256 CHAR(64) NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    mapping_method TEXT NOT NULL CHECK (
        mapping_method IN ('EXACT_PROVIDER_ID', 'MANUAL_EVIDENCE')
    ),
    mapping_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED'
        CHECK (
            mapping_status IN (
                'SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED',
                'REVIEW_REQUIRED', 'CONFLICT', 'REJECTED'
            )
        ),
    evidence_uri TEXT,
    evidence_sha256 CHAR(64) CHECK (
        evidence_sha256 IS NULL OR evidence_sha256 ~ '^[0-9a-f]{64}$'
    ),
    reviewer_id TEXT,
    reviewed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (
        provider, source_id, provider_competition_id,
        source_observation_id, rights_approval_id
    ) REFERENCES veltrix_ai_analyst.provider_competitions (
        provider, source_id, provider_competition_id,
        source_observation_id, rights_approval_id
    ) ON DELETE RESTRICT,
    CHECK (
        (reviewer_id IS NULL AND reviewed_at IS NULL)
        OR
        (reviewer_id IS NOT NULL AND length(btrim(reviewer_id)) > 0 AND reviewed_at IS NOT NULL)
    ),
    CHECK (
        mapping_status NOT IN ('SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED')
        OR (
            reviewer_id IS NOT NULL AND evidence_uri IS NOT NULL AND evidence_uri <> ''
            AND evidence_sha256 IS NOT NULL
        )
    )
);
CREATE INDEX provider_competition_identity_links_canonical_idx
    ON veltrix_ai_analyst.provider_competition_identity_links(canonical_competition_id);

CREATE TABLE veltrix_ai_analyst.canonical_fixture_sources (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    canonical_fixture_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_fixtures(id) ON DELETE RESTRICT,
    provider_fixture_row_id BIGINT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    source_id TEXT NOT NULL,
    provider_fixture_id TEXT NOT NULL,
    source_observation_id BIGINT NOT NULL,
    source_sighting_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observation_sightings(id) ON DELETE RESTRICT,
    provider_response_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT,
    rights_approval_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.source_approvals(approval_id) ON DELETE RESTRICT,
    payload_sha256 CHAR(64) NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    mapping_method TEXT NOT NULL CHECK (
        mapping_method IN ('EXACT_PROVIDER_FIXTURE_ID', 'MANUAL_EVIDENCE')
    ),
    mapping_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED'
        CHECK (mapping_status IN ('SOURCE_ROW_LINKED', 'REVIEW_REQUIRED', 'CONFLICT', 'REJECTED')),
    evidence_uri TEXT,
    evidence_sha256 CHAR(64) CHECK (
        evidence_sha256 IS NULL OR evidence_sha256 ~ '^[0-9a-f]{64}$'
    ),
    reviewer_id TEXT,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (
        provider_fixture_row_id, provider, source_id, provider_fixture_id,
        source_observation_id, rights_approval_id
    ) REFERENCES veltrix_ai_analyst.provider_fixtures (
        id, provider, source_id, provider_fixture_id,
        source_observation_id, rights_approval_id
    ) ON DELETE RESTRICT,
    CHECK (
        (reviewer_id IS NULL AND reviewed_at IS NULL)
        OR
        (reviewer_id IS NOT NULL AND length(btrim(reviewer_id)) > 0 AND reviewed_at IS NOT NULL)
    ),
    CHECK (
        mapping_status <> 'SOURCE_ROW_LINKED'
        OR (
            reviewer_id IS NOT NULL AND evidence_uri IS NOT NULL AND evidence_uri <> ''
            AND evidence_sha256 IS NOT NULL
        )
    )
);
CREATE INDEX canonical_fixture_sources_canonical_idx
    ON veltrix_ai_analyst.canonical_fixture_sources(canonical_fixture_id);

-- The same trigger validates exact observation/sighting/response/hash provenance
-- for every canonical provider link. The composite foreign keys above bind each
-- link to the exact provider projection row and its rights approval.
CREATE OR REPLACE FUNCTION veltrix_ai_analyst.enforce_canonical_link_provenance()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    observation RECORD;
    sighting RECORD;
    response RECORD;
BEGIN
    SELECT provider, source_id, payload_sha256
    INTO observation
    FROM veltrix_ai_analyst.source_observations
    WHERE id = NEW.source_observation_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'CANONICAL_SOURCE_OBSERVATION_NOT_FOUND';
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

    SELECT provider, source_id, http_status
    INTO response
    FROM veltrix_ai_analyst.provider_responses
    WHERE id = NEW.provider_response_id;

    IF NOT FOUND
       OR response.provider <> observation.provider
       OR response.source_id <> observation.source_id
       OR response.provider <> NEW.provider
       OR response.source_id <> NEW.source_id
       OR response.http_status NOT BETWEEN 200 AND 299
       OR observation.payload_sha256 <> NEW.payload_sha256 THEN
        RAISE EXCEPTION 'CANONICAL_SOURCE_RESPONSE_OR_HASH_MISMATCH';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER provider_team_identity_link_provenance_guard
    BEFORE INSERT ON veltrix_ai_analyst.provider_team_identity_links
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.enforce_canonical_link_provenance();
CREATE TRIGGER provider_competition_identity_link_provenance_guard
    BEFORE INSERT ON veltrix_ai_analyst.provider_competition_identity_links
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.enforce_canonical_link_provenance();
CREATE TRIGGER canonical_fixture_source_provenance_guard
    BEFORE INSERT ON veltrix_ai_analyst.canonical_fixture_sources
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.enforce_canonical_link_provenance();

-- Link decisions are append-only. A correction is a new event that supersedes
-- an earlier event; the underlying candidate link is never rewritten.
CREATE TABLE veltrix_ai_analyst.canonical_identity_review_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    team_identity_link_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_team_identity_links(id) ON DELETE RESTRICT,
    competition_identity_link_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_competition_identity_links(id) ON DELETE RESTRICT,
    fixture_source_link_id BIGINT
        REFERENCES veltrix_ai_analyst.canonical_fixture_sources(id) ON DELETE RESTRICT,
    decision TEXT NOT NULL CHECK (
        decision IN (
            'SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED',
            'SOURCE_FIXTURE_LINK_REVIEWED', 'REVIEW_REQUIRED', 'CONFLICT', 'REJECTED'
        )
    ),
    reviewer_id TEXT NOT NULL CHECK (length(btrim(reviewer_id)) > 0),
    reviewed_at TIMESTAMPTZ NOT NULL,
    evidence_uri TEXT NOT NULL CHECK (length(btrim(evidence_uri)) > 0),
    evidence_sha256 CHAR(64) NOT NULL CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    supersedes_event_id BIGINT
        REFERENCES veltrix_ai_analyst.canonical_identity_review_events(id) ON DELETE RESTRICT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (num_nonnulls(
        team_identity_link_id, competition_identity_link_id, fixture_source_link_id
    ) = 1),
    CHECK (
        (team_identity_link_id IS NOT NULL AND decision IN (
            'SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED', 'REVIEW_REQUIRED', 'CONFLICT', 'REJECTED'
        ))
        OR
        (competition_identity_link_id IS NOT NULL AND decision IN (
            'SOURCE_IDENTITY_REVIEWED', 'REAL_WORLD_IDENTITY_VERIFIED', 'REVIEW_REQUIRED', 'CONFLICT', 'REJECTED'
        ))
        OR
        (fixture_source_link_id IS NOT NULL AND decision IN (
            'SOURCE_FIXTURE_LINK_REVIEWED', 'REVIEW_REQUIRED', 'CONFLICT', 'REJECTED'
        ))
    )
);

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.validate_canonical_review_supersession()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    prior RECORD;
BEGIN
    IF NEW.supersedes_event_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT team_identity_link_id, competition_identity_link_id,
           fixture_source_link_id, reviewed_at
    INTO prior
    FROM veltrix_ai_analyst.canonical_identity_review_events
    WHERE id = NEW.supersedes_event_id;

    IF NOT FOUND
       OR prior.team_identity_link_id IS DISTINCT FROM NEW.team_identity_link_id
       OR prior.competition_identity_link_id IS DISTINCT FROM NEW.competition_identity_link_id
       OR prior.fixture_source_link_id IS DISTINCT FROM NEW.fixture_source_link_id
       OR prior.reviewed_at >= NEW.reviewed_at THEN
        RAISE EXCEPTION 'CANONICAL_REVIEW_SUPERSESSION_TARGET_MISMATCH';
    END IF;

    RETURN NEW;
END;
$$;
CREATE TRIGGER canonical_review_supersession_guard
    BEFORE INSERT ON veltrix_ai_analyst.canonical_identity_review_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.validate_canonical_review_supersession();

CREATE TRIGGER provider_team_identity_links_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.provider_team_identity_links
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();
CREATE TRIGGER provider_competition_identity_links_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.provider_competition_identity_links
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();
CREATE TRIGGER canonical_fixture_sources_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.canonical_fixture_sources
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();
CREATE TRIGGER canonical_identity_review_events_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.canonical_identity_review_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE VIEW veltrix_ai_analyst.effective_provider_team_identity_links AS
SELECT link.*,
       COALESCE(event.decision, link.mapping_status) AS effective_mapping_status,
       event.reviewer_id AS latest_reviewer_id,
       event.reviewed_at AS latest_reviewed_at,
       event.evidence_uri AS latest_evidence_uri,
       event.evidence_sha256 AS latest_evidence_sha256
FROM veltrix_ai_analyst.provider_team_identity_links link
LEFT JOIN LATERAL (
    SELECT decision, reviewer_id, reviewed_at, evidence_uri, evidence_sha256
    FROM veltrix_ai_analyst.canonical_identity_review_events
    WHERE team_identity_link_id = link.id
    ORDER BY reviewed_at DESC, id DESC
    LIMIT 1
) event ON TRUE;

CREATE VIEW veltrix_ai_analyst.effective_provider_competition_identity_links AS
SELECT link.*,
       COALESCE(event.decision, link.mapping_status) AS effective_mapping_status,
       event.reviewer_id AS latest_reviewer_id,
       event.reviewed_at AS latest_reviewed_at,
       event.evidence_uri AS latest_evidence_uri,
       event.evidence_sha256 AS latest_evidence_sha256
FROM veltrix_ai_analyst.provider_competition_identity_links link
LEFT JOIN LATERAL (
    SELECT decision, reviewer_id, reviewed_at, evidence_uri, evidence_sha256
    FROM veltrix_ai_analyst.canonical_identity_review_events
    WHERE competition_identity_link_id = link.id
    ORDER BY reviewed_at DESC, id DESC
    LIMIT 1
) event ON TRUE;

CREATE VIEW veltrix_ai_analyst.effective_canonical_fixture_sources AS
SELECT link.*,
       COALESCE(event.decision, link.mapping_status) AS effective_mapping_status,
       event.reviewer_id AS latest_reviewer_id,
       event.reviewed_at AS latest_reviewed_at,
       event.evidence_uri AS latest_evidence_uri,
       event.evidence_sha256 AS latest_evidence_sha256
FROM veltrix_ai_analyst.canonical_fixture_sources link
LEFT JOIN LATERAL (
    SELECT decision, reviewer_id, reviewed_at, evidence_uri, evidence_sha256
    FROM veltrix_ai_analyst.canonical_identity_review_events
    WHERE fixture_source_link_id = link.id
    ORDER BY reviewed_at DESC, id DESC
    LIMIT 1
) event ON TRUE;
