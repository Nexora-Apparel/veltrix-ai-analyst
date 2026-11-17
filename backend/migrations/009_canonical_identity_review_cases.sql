-- VELTRIX AI ANALYST: evidence-backed identity review queue.
-- This migration records review cases and recommendations only. It does not
-- merge identities, reparent fixtures, alter source rows, or certify PIT data.

CREATE TABLE veltrix_ai_analyst.canonical_identity_review_cases (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_key TEXT NOT NULL UNIQUE,
    case_type TEXT NOT NULL CHECK (
        case_type IN (
            'TEAM_ALIAS_CANDIDATE',
            'TEAM_REAL_WORLD_IDENTITY_CANDIDATE',
            'COMPETITION_REAL_WORLD_IDENTITY_CANDIDATE',
            'FIXTURE_DUPLICATE_CANDIDATE',
            'SEASON_COVERAGE_RECONCILIATION',
            'PIT_TIMESTAMP_GAP'
        )
    ),
    primary_team_identity_link_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_team_identity_links(id) ON DELETE RESTRICT,
    related_team_identity_link_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_team_identity_links(id) ON DELETE RESTRICT,
    competition_identity_link_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_competition_identity_links(id) ON DELETE RESTRICT,
    primary_fixture_source_link_id BIGINT
        REFERENCES veltrix_ai_analyst.canonical_fixture_sources(id) ON DELETE RESTRICT,
    related_fixture_source_link_id BIGINT
        REFERENCES veltrix_ai_analyst.canonical_fixture_sources(id) ON DELETE RESTRICT,
    recommended_action TEXT NOT NULL,
    evidence_uris TEXT[] NOT NULL CHECK (cardinality(evidence_uris) > 0),
    evidence_summary TEXT NOT NULL CHECK (length(btrim(evidence_summary)) > 0),
    evidence_sha256 CHAR(64) CHECK (
        evidence_sha256 IS NULL OR evidence_sha256 ~ '^[0-9a-f]{64}$'
    ),
    human_review_required BOOLEAN NOT NULL DEFAULT TRUE,
    created_by TEXT NOT NULL DEFAULT 'automated_evidence_audit',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (case_type = 'TEAM_ALIAS_CANDIDATE'
            AND primary_team_identity_link_id IS NOT NULL
            AND related_team_identity_link_id IS NOT NULL
            AND primary_team_identity_link_id <> related_team_identity_link_id
            AND competition_identity_link_id IS NULL
            AND primary_fixture_source_link_id IS NULL
            AND related_fixture_source_link_id IS NULL)
        OR
        (case_type = 'TEAM_REAL_WORLD_IDENTITY_CANDIDATE'
            AND primary_team_identity_link_id IS NOT NULL
            AND related_team_identity_link_id IS NULL
            AND competition_identity_link_id IS NULL
            AND primary_fixture_source_link_id IS NULL
            AND related_fixture_source_link_id IS NULL)
        OR
        (case_type = 'COMPETITION_REAL_WORLD_IDENTITY_CANDIDATE'
            AND primary_team_identity_link_id IS NULL
            AND related_team_identity_link_id IS NULL
            AND competition_identity_link_id IS NOT NULL
            AND primary_fixture_source_link_id IS NULL
            AND related_fixture_source_link_id IS NULL)
        OR
        (case_type = 'FIXTURE_DUPLICATE_CANDIDATE'
            AND primary_fixture_source_link_id IS NOT NULL
            AND related_fixture_source_link_id IS NOT NULL
            AND primary_fixture_source_link_id <> related_fixture_source_link_id
            AND primary_team_identity_link_id IS NULL
            AND related_team_identity_link_id IS NULL
            AND competition_identity_link_id IS NULL)
        OR
        (case_type IN ('SEASON_COVERAGE_RECONCILIATION', 'PIT_TIMESTAMP_GAP')
            AND primary_team_identity_link_id IS NULL
            AND related_team_identity_link_id IS NULL
            AND competition_identity_link_id IS NULL
            AND primary_fixture_source_link_id IS NULL
            AND related_fixture_source_link_id IS NULL)
    )
);

CREATE INDEX canonical_identity_review_cases_type_idx
    ON veltrix_ai_analyst.canonical_identity_review_cases(case_type, created_at);

CREATE TABLE veltrix_ai_analyst.canonical_identity_review_case_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_identity_review_cases(id) ON DELETE RESTRICT,
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'AUTOMATED_RECOMMENDATION',
            'HUMAN_CONFIRMED',
            'HUMAN_REJECTED',
            'MORE_EVIDENCE_REQUIRED',
            'DEFERRED'
        )
    ),
    reviewer_type TEXT NOT NULL CHECK (reviewer_type IN ('AUTOMATED_SYSTEM', 'HUMAN')),
    reviewer_id TEXT NOT NULL CHECK (length(btrim(reviewer_id)) > 0),
    reviewed_at TIMESTAMPTZ NOT NULL,
    evidence_uri TEXT NOT NULL CHECK (length(btrim(evidence_uri)) > 0),
    evidence_sha256 CHAR(64) CHECK (
        evidence_sha256 IS NULL OR evidence_sha256 ~ '^[0-9a-f]{64}$'
    ),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (event_type = 'AUTOMATED_RECOMMENDATION' AND reviewer_type = 'AUTOMATED_SYSTEM')
        OR
        (event_type <> 'AUTOMATED_RECOMMENDATION' AND reviewer_type = 'HUMAN')
    ),
    CHECK (
        event_type NOT IN ('HUMAN_CONFIRMED', 'HUMAN_REJECTED')
        OR evidence_sha256 IS NOT NULL
    ),
    UNIQUE (case_id, event_type, reviewer_id)
);

CREATE INDEX canonical_identity_review_case_events_latest_idx
    ON veltrix_ai_analyst.canonical_identity_review_case_events(case_id, reviewed_at DESC, id DESC);

CREATE TRIGGER canonical_identity_review_cases_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.canonical_identity_review_cases
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE TRIGGER canonical_identity_review_case_events_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.canonical_identity_review_case_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE VIEW veltrix_ai_analyst.effective_canonical_identity_review_cases AS
SELECT
    review_case.*,
    COALESCE(latest.event_type, 'MORE_EVIDENCE_REQUIRED') AS latest_event_type,
    latest.reviewer_type AS latest_reviewer_type,
    latest.reviewer_id AS latest_reviewer_id,
    latest.reviewed_at AS latest_reviewed_at,
    latest.evidence_uri AS latest_evidence_uri,
    latest.notes AS latest_notes,
    CASE
        WHEN latest.event_type = 'HUMAN_CONFIRMED' THEN 'HUMAN_CONFIRMED'
        WHEN latest.event_type = 'HUMAN_REJECTED' THEN 'HUMAN_REJECTED'
        WHEN latest.event_type = 'DEFERRED' THEN 'DEFERRED'
        WHEN latest.event_type = 'MORE_EVIDENCE_REQUIRED' THEN 'MORE_EVIDENCE_REQUIRED'
        ELSE 'HUMAN_REVIEW_REQUIRED'
    END AS effective_case_status
FROM veltrix_ai_analyst.canonical_identity_review_cases review_case
LEFT JOIN LATERAL (
    SELECT event_type, reviewer_type, reviewer_id, reviewed_at, evidence_uri, notes
    FROM veltrix_ai_analyst.canonical_identity_review_case_events event
    WHERE event.case_id = review_case.id
    ORDER BY event.reviewed_at DESC, event.id DESC
    LIMIT 1
) latest ON TRUE;

-- Provenance is machine-verifiable independently of real-world identity.
-- These views distinguish an intact provider-local identity from a club identity
-- that still requires an evidence-backed human decision.
CREATE VIEW veltrix_ai_analyst.canonical_team_identity_provenance_audit AS
SELECT
    link.id AS identity_link_id,
    link.provider,
    link.source_id,
    link.provider_team_id,
    team.name AS provider_team_name,
    link.canonical_team_id,
    canonical.display_name AS source_local_display_name,
    link.source_observation_id,
    link.source_sighting_id,
    link.provider_response_id,
    link.payload_sha256,
    CASE
        WHEN observation.id IS NOT NULL
         AND observation.provider = link.provider
         AND observation.source_id = link.source_id
         AND observation.data_type = 'team_catalogue'
         AND observation.entity_type = 'team'
         AND observation.provider_entity_id = link.provider_team_id
         AND observation.payload_sha256 = link.payload_sha256
         AND observation.rights_approval_id = link.rights_approval_id
         AND sighting.id IS NOT NULL
         AND sighting.source_observation_id = link.source_observation_id
         AND sighting.provider_response_id = link.provider_response_id
         AND sighting.payload_sha256 = link.payload_sha256
         AND response.provider = link.provider
         AND response.source_id = link.source_id
         AND response.rights_approval_id = link.rights_approval_id
         AND response.http_status BETWEEN 200 AND 299
        THEN 'PROVENANCE_VERIFIED'
        ELSE 'PROVENANCE_INVALID'
    END AS source_identity_provenance_status,
    COALESCE(review.decision, 'REAL_WORLD_IDENTITY_REVIEW_REQUIRED') AS real_world_identity_status
FROM veltrix_ai_analyst.provider_team_identity_links link
JOIN veltrix_ai_analyst.provider_teams team
  ON team.provider = link.provider
 AND team.source_id = link.source_id
 AND team.provider_team_id = link.provider_team_id
JOIN veltrix_ai_analyst.canonical_teams canonical
  ON canonical.id = link.canonical_team_id
LEFT JOIN veltrix_ai_analyst.source_observations observation
  ON observation.id = link.source_observation_id
LEFT JOIN veltrix_ai_analyst.source_observation_sightings sighting
  ON sighting.id = link.source_sighting_id
LEFT JOIN veltrix_ai_analyst.provider_responses response
  ON response.id = link.provider_response_id
LEFT JOIN LATERAL (
    SELECT event.decision
    FROM veltrix_ai_analyst.canonical_identity_review_events event
    WHERE event.team_identity_link_id = link.id
    ORDER BY event.reviewed_at DESC, event.id DESC
    LIMIT 1
) review ON TRUE;

CREATE VIEW veltrix_ai_analyst.canonical_competition_identity_provenance_audit AS
SELECT
    link.id AS identity_link_id,
    link.provider,
    link.source_id,
    link.provider_competition_id,
    competition.name AS provider_competition_name,
    link.canonical_competition_id,
    canonical.display_name AS source_local_display_name,
    link.source_observation_id,
    link.source_sighting_id,
    link.provider_response_id,
    link.payload_sha256,
    CASE
        WHEN observation.id IS NOT NULL
         AND observation.provider = link.provider
         AND observation.source_id = link.source_id
         AND observation.data_type = 'competition_catalogue'
         AND observation.entity_type = 'competition'
         AND observation.provider_entity_id = link.provider_competition_id
         AND observation.payload_sha256 = link.payload_sha256
         AND observation.rights_approval_id = link.rights_approval_id
         AND sighting.id IS NOT NULL
         AND sighting.source_observation_id = link.source_observation_id
         AND sighting.provider_response_id = link.provider_response_id
         AND sighting.payload_sha256 = link.payload_sha256
         AND response.provider = link.provider
         AND response.source_id = link.source_id
         AND response.rights_approval_id = link.rights_approval_id
         AND response.http_status BETWEEN 200 AND 299
        THEN 'PROVENANCE_VERIFIED'
        ELSE 'PROVENANCE_INVALID'
    END AS source_identity_provenance_status,
    COALESCE(review.decision, 'REAL_WORLD_IDENTITY_REVIEW_REQUIRED') AS real_world_identity_status
FROM veltrix_ai_analyst.provider_competition_identity_links link
JOIN veltrix_ai_analyst.provider_competitions competition
  ON competition.provider = link.provider
 AND competition.source_id = link.source_id
 AND competition.provider_competition_id = link.provider_competition_id
JOIN veltrix_ai_analyst.canonical_competitions canonical
  ON canonical.id = link.canonical_competition_id
LEFT JOIN veltrix_ai_analyst.source_observations observation
  ON observation.id = link.source_observation_id
LEFT JOIN veltrix_ai_analyst.source_observation_sightings sighting
  ON sighting.id = link.source_sighting_id
LEFT JOIN veltrix_ai_analyst.provider_responses response
  ON response.id = link.provider_response_id
LEFT JOIN LATERAL (
    SELECT event.decision
    FROM veltrix_ai_analyst.canonical_identity_review_events event
    WHERE event.competition_identity_link_id = link.id
    ORDER BY event.reviewed_at DESC, event.id DESC
    LIMIT 1
) review ON TRUE;

CREATE VIEW veltrix_ai_analyst.canonical_fixture_source_provenance_audit AS
SELECT
    link.id AS fixture_source_link_id,
    link.provider_fixture_id,
    link.canonical_fixture_id,
    fixture.kickoff_at AS provider_kickoff_at,
    canonical.kickoff_at AS canonical_kickoff_at,
    fixture.status AS provider_status,
    fixture.home_goals,
    fixture.away_goals,
    CASE
        WHEN observation.id IS NOT NULL
         AND observation.provider = link.provider
         AND observation.source_id = link.source_id
         AND observation.data_type = 'fixtures_and_results'
         AND observation.entity_type = 'fixture'
         AND observation.provider_entity_id = link.provider_fixture_id
         AND observation.payload_sha256 = link.payload_sha256
         AND observation.rights_approval_id = link.rights_approval_id
         AND sighting.id IS NOT NULL
         AND sighting.source_observation_id = link.source_observation_id
         AND sighting.provider_response_id = link.provider_response_id
         AND sighting.payload_sha256 = link.payload_sha256
         AND response.provider = link.provider
         AND response.source_id = link.source_id
         AND response.rights_approval_id = link.rights_approval_id
         AND response.http_status BETWEEN 200 AND 299
         AND fixture.kickoff_at = canonical.kickoff_at
         AND fixture.status = canonical.status
         AND fixture.home_goals IS NOT DISTINCT FROM canonical.home_goals
         AND fixture.away_goals IS NOT DISTINCT FROM canonical.away_goals
        THEN 'PROVENANCE_VERIFIED'
        ELSE 'PROVENANCE_INVALID'
    END AS source_fixture_provenance_status,
    COALESCE(review.decision, 'SOURCE_FIXTURE_REVIEW_REQUIRED') AS effective_review_status
FROM veltrix_ai_analyst.canonical_fixture_sources link
JOIN veltrix_ai_analyst.provider_fixtures fixture
  ON fixture.id = link.provider_fixture_row_id
JOIN veltrix_ai_analyst.canonical_fixtures canonical
  ON canonical.id = link.canonical_fixture_id
LEFT JOIN veltrix_ai_analyst.source_observations observation
  ON observation.id = link.source_observation_id
LEFT JOIN veltrix_ai_analyst.source_observation_sightings sighting
  ON sighting.id = link.source_sighting_id
LEFT JOIN veltrix_ai_analyst.provider_responses response
  ON response.id = link.provider_response_id
LEFT JOIN LATERAL (
    SELECT event.decision
    FROM veltrix_ai_analyst.canonical_identity_review_events event
    WHERE event.fixture_source_link_id = link.id
    ORDER BY event.reviewed_at DESC, event.id DESC
    LIMIT 1
) review ON TRUE;

CREATE VIEW veltrix_ai_analyst.canonical_fixture_duplicate_case_audit AS
SELECT
    review_case.case_key,
    primary_link.provider_fixture_id AS primary_provider_fixture_id,
    duplicate_link.provider_fixture_id AS duplicate_provider_fixture_id,
    primary_fixture.kickoff_at AS primary_provider_kickoff_at,
    duplicate_fixture.kickoff_at AS duplicate_provider_kickoff_at,
    primary_fixture.status AS primary_provider_status,
    duplicate_fixture.status AS duplicate_provider_status,
    primary_fixture.home_goals,
    primary_fixture.away_goals,
    review_case.recommended_action,
    review_case.evidence_uris,
    review_case.evidence_summary,
    review_case.human_review_required,
    effective.effective_case_status
FROM veltrix_ai_analyst.canonical_identity_review_cases review_case
JOIN veltrix_ai_analyst.canonical_fixture_sources primary_link
  ON primary_link.id = review_case.primary_fixture_source_link_id
JOIN veltrix_ai_analyst.canonical_fixture_sources duplicate_link
  ON duplicate_link.id = review_case.related_fixture_source_link_id
JOIN veltrix_ai_analyst.provider_fixtures primary_fixture
  ON primary_fixture.id = primary_link.provider_fixture_row_id
JOIN veltrix_ai_analyst.provider_fixtures duplicate_fixture
  ON duplicate_fixture.id = duplicate_link.provider_fixture_row_id
JOIN veltrix_ai_analyst.effective_canonical_identity_review_cases effective
  ON effective.id = review_case.id
WHERE review_case.case_type = 'FIXTURE_DUPLICATE_CANDIDATE';

-- Four UNKNOWN rows are duplicate/stale candidates: three match exact provider team IDs;
-- the Goiás-América pair uses a second provider ID supported by official alias evidence.
-- Official CBF match pages establish one real fixture and the settled result.
-- We stage evidence and a recommended deduplication only; no source or canonical
-- row is rewritten, and a human must confirm before any canonical resolution.
INSERT INTO veltrix_ai_analyst.canonical_identity_review_cases (
    case_key, case_type, primary_fixture_source_link_id, related_fixture_source_link_id,
    recommended_action, evidence_uris, evidence_summary
)
SELECT
    candidate.case_key,
    'FIXTURE_DUPLICATE_CANDIDATE',
    primary_link.id,
    duplicate_link.id,
    'EXCLUDE_DUPLICATE_SOURCE_ROW_AFTER_HUMAN_CONFIRMATION',
    ARRAY[candidate.evidence_uri],
    candidate.evidence_summary
FROM (VALUES
    (
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_AMERICA_MG',
        '3116209225', '2341822348',
        'https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/goias-x-america/832843',
        'CBF records one Round 1 Goiás 3-1 América MG fixture on 2026-03-22 at Hailé Pinheiro. Provider fixture 3116209225 is FINISHED 3-1; provider fixture 2341822348 is UNKNOWN, same teams, 85 seconds later. This is one official match represented by two provider IDs.'
    ),
    (
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_FORTALEZA_LONDRINA',
        '1587564237', '2336910968',
        'https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-londrina-saf/832976',
        'CBF records Fortaleza 3-0 Londrina on 2026-05-23, Round 10. Provider fixture 1587564237 is FINISHED 3-0; provider fixture 2336910968 is UNKNOWN with the same team IDs but an August timestamp. The August row is a stale or duplicate representation of the May match.'
    ),
    (
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_FORTALEZA_BOTAFOGO',
        '236839304', '933498248',
        'https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-botafogo/833076',
        'CBF records Fortaleza 1-0 Botafogo SP on 2026-07-28, Round 20. Provider fixture 236839304 is FINISHED 1-0; provider fixture 933498248 is UNKNOWN with the same team IDs but an August timestamp. The August row is a stale or duplicate representation of the July match.'
    ),
    (
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_CEARA_LONDRINA',
        '553958702', '1988139832',
        'https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/ceara-x-londrina-saf/833116',
        'CBF records Ceará 2-1 Londrina on 2026-08-22, Round 24. Provider fixture 553958702 is FINISHED 2-1; provider fixture 1988139832 is UNKNOWN with the same team IDs but an August 20 timestamp. The earlier UNKNOWN row is a stale or duplicate representation of the August 22 match.'
    )
) AS candidate(case_key, primary_fixture_id, duplicate_fixture_id, evidence_uri, evidence_summary)
JOIN veltrix_ai_analyst.canonical_fixture_sources primary_link
  ON primary_link.provider = '5DollarFootballAPI'
 AND primary_link.source_id = '5dollarfootballapi'
 AND primary_link.provider_fixture_id = candidate.primary_fixture_id
JOIN veltrix_ai_analyst.canonical_fixture_sources duplicate_link
  ON duplicate_link.provider = '5DollarFootballAPI'
 AND duplicate_link.source_id = '5dollarfootballapi'
 AND duplicate_link.provider_fixture_id = candidate.duplicate_fixture_id
ON CONFLICT (case_key) DO NOTHING;

-- The source's 21st provider ID is not a 21st club: it appears only on the
-- duplicate Goiás-América row. CBF's official match record identifies América MG.
-- Keep both provider IDs and canonical placeholders intact pending human review.
INSERT INTO veltrix_ai_analyst.canonical_identity_review_cases (
    case_key, case_type, primary_team_identity_link_id, related_team_identity_link_id,
    recommended_action, evidence_uris, evidence_summary
)
SELECT
    'BRAZIL_SERIE_B_RUN_3_TEAM_ALIAS_AMERICA_MG',
    'TEAM_ALIAS_CANDIDATE',
    primary_link.id,
    alias_link.id,
    'MAP_ALIAS_PROVIDER_ID_TO_AMERICA_MINEIRO_AFTER_HUMAN_CONFIRMATION',
    ARRAY[
        'https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/goias-x-america/832843',
        'https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Brasileiro_Serie_B_2026_23_09_378b396600.pdf'
    ],
    'CBF identifies the sole Round 1 fixture as Goiás 3-1 América MG. Provider team ID 1102583842 (America MG) appears in 37 fixtures; provider team ID 3808811746 (América Mineiro) appears only in the duplicate UNKNOWN Goiás row. Strong alias evidence; preserve both source identities until a human confirms the alias.'
FROM veltrix_ai_analyst.provider_team_identity_links primary_link
JOIN veltrix_ai_analyst.provider_team_identity_links alias_link
  ON alias_link.provider = primary_link.provider
 AND alias_link.source_id = primary_link.source_id
WHERE primary_link.provider = '5DollarFootballAPI'
  AND primary_link.source_id = '5dollarfootballapi'
  AND primary_link.provider_team_id = '1102583842'
  AND alias_link.provider_team_id = '3808811746'
ON CONFLICT (case_key) DO NOTHING;

-- Stage individual team and competition mappings for explicit human review.
-- These are candidate crosswalks, not automatic identity assertions.
INSERT INTO veltrix_ai_analyst.canonical_identity_review_cases (
    case_key, case_type, primary_team_identity_link_id,
    recommended_action, evidence_uris, evidence_summary
)
SELECT
    'BRAZIL_SERIE_B_RUN_3_TEAM_IDENTITY_' || link.provider_team_id,
    'TEAM_REAL_WORLD_IDENTITY_CANDIDATE',
    link.id,
    'VERIFY_REAL_WORLD_TEAM_IDENTITY',
    ARRAY[
        'https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026?doc=Tabela+Detalhada',
        'https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Brasileiro_Serie_B_2026_23_09_378b396600.pdf'
    ],
    'Provider team ID ' || link.provider_team_id || ' is labelled "' || team.name ||
    '" in the immutable source catalogue and appears in the imported fixture graph. Compare the club name and home/away schedule against the official CBF 2026 Série B fixture table before confirming real-world identity.'
FROM veltrix_ai_analyst.provider_team_identity_links link
JOIN veltrix_ai_analyst.provider_teams team
  ON team.provider = link.provider
 AND team.source_id = link.source_id
 AND team.provider_team_id = link.provider_team_id
WHERE link.provider = '5DollarFootballAPI'
  AND link.source_id = '5dollarfootballapi'
  AND link.provider_team_id <> '3808811746'
ON CONFLICT (case_key) DO NOTHING;

INSERT INTO veltrix_ai_analyst.canonical_identity_review_cases (
    case_key, case_type, competition_identity_link_id,
    recommended_action, evidence_uris, evidence_summary
)
SELECT
    'BRAZIL_SERIE_B_RUN_3_COMPETITION_IDENTITY_522514093',
    'COMPETITION_REAL_WORLD_IDENTITY_CANDIDATE',
    link.id,
    'VERIFY_BRAZIL_SERIE_B_2026_COMPETITION_IDENTITY_AND_SEASON',
    ARRAY[
        'https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026?doc=Tabela+Detalhada',
        'https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Brasileiro_Serie_B_2026_23_09_378b396600.pdf'
    ],
    'Provider competition ID 522514093 is labelled Brazil Serie B in the imported source. CBF official 2026 Série B schedule is independent evidence for the competition and season context; human reviewer must verify the provider competition identity and record the season scope explicitly.'
FROM veltrix_ai_analyst.provider_competition_identity_links link
WHERE link.provider = '5DollarFootballAPI'
  AND link.source_id = '5dollarfootballapi'
  AND link.provider_competition_id = '522514093'
ON CONFLICT (case_key) DO NOTHING;

INSERT INTO veltrix_ai_analyst.canonical_identity_review_cases (
    case_key, case_type, recommended_action, evidence_uris, evidence_summary
)
VALUES
(
    'BRAZIL_SERIE_B_RUN_3_COVERAGE_2026',
    'SEASON_COVERAGE_RECONCILIATION',
    'RECONCILE_ALL_370_FINISHED_ROWS_TO_CBF_ROUNDS_1_TO_37_BEFORE_CERTIFYING_COVERAGE',
    ARRAY[
        'https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026?doc=Tabela+Detalhada',
        'https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Brasileiro_Serie_B_2026_23_09_378b396600.pdf',
        'https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/botafogo-x-londrina-saf/833272'
    ],
    'The imported interval ends 2026-11-09 and contains 370 FINISHED records: 20 provider team IDs, exactly 37 appearances per team, 370 distinct ordered home/away pairs, and zero repeated ordered pairs. All 10 Round 37 pairings match the official CBF Round 37 schedule; the detailed CBF match record dates Botafogo SP-Londrina to 2026-11-05, within the import window. Round 38 is 2026-11-14 and outside run 3. Four UNKNOWN provider rows are duplicate candidates. These structural checks are strong coverage evidence but do not replace a full 370-pair fixture-by-fixture official schedule reconciliation.'
),
(
    'BRAZIL_SERIE_B_RUN_3_PIT_TIMESTAMP_GAP',
    'PIT_TIMESTAMP_GAP',
    'KEEP_ALL_374_OBSERVATIONS_OUT_OF_PREMATCH_FEATURES_UNTIL_SOURCE_PUBLICATION_AND_AVAILABILITY_TIMESTAMPS_ARE_VERIFIED',
    ARRAY['urn:veltrix-ai-analyst:neon:source-observation-pit-audit:2026-11-17'],
    'Read-only production audit found 374 fixture observations and 374 sightings, with zero source_published_at, zero available_at, zero PIT-certifiable observations and zero PIT-certifiable sightings. Retrieval time and kickoff time are not substitutes.'
)
ON CONFLICT (case_key) DO NOTHING;

INSERT INTO veltrix_ai_analyst.canonical_identity_review_case_events (
    case_id, event_type, reviewer_type, reviewer_id, reviewed_at, evidence_uri, notes
)
SELECT
    review_case.id,
    'AUTOMATED_RECOMMENDATION',
    'AUTOMATED_SYSTEM',
    'VELTRIX_AI_ANALYST_EVIDENCE_AUDIT',
    NOW(),
    review_case.evidence_uris[1],
    'Evidence gathered and recommendation staged. This is not a human identity decision; no canonical links or source rows were changed.'
FROM veltrix_ai_analyst.canonical_identity_review_cases review_case
WHERE (
    review_case.case_key IN (
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_AMERICA_MG',
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_FORTALEZA_LONDRINA',
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_FORTALEZA_BOTAFOGO',
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_CEARA_LONDRINA',
        'BRAZIL_SERIE_B_RUN_3_TEAM_ALIAS_AMERICA_MG',
        'BRAZIL_SERIE_B_RUN_3_COMPETITION_IDENTITY_522514093',
        'BRAZIL_SERIE_B_RUN_3_COVERAGE_2026',
        'BRAZIL_SERIE_B_RUN_3_PIT_TIMESTAMP_GAP'
    )
    OR review_case.case_key LIKE 'BRAZIL_SERIE_B_RUN_3_TEAM_IDENTITY_%'
)
ON CONFLICT (case_id, event_type, reviewer_id) DO NOTHING;
