-- Automated, evidence-backed identity adjudication without canonical merges.
-- Decisions are append-only, policy-versioned and evidence-hashed. Automated
-- confirmation/deferment closes the human action queue but never authorizes
-- destructive alias merging, fixture deduplication or PIT timestamp fabrication.

ALTER TABLE veltrix_ai_analyst.canonical_identity_review_case_events
    ADD COLUMN policy_version TEXT,
    ADD COLUMN confidence NUMERIC(5,4),
    ADD COLUMN decision_basis TEXT;

ALTER TABLE veltrix_ai_analyst.canonical_identity_review_case_events
    DROP CONSTRAINT canonical_identity_review_case_events_event_type_check,
    DROP CONSTRAINT canonical_identity_review_case_events_check,
    DROP CONSTRAINT canonical_identity_review_case_events_check1;

ALTER TABLE veltrix_ai_analyst.canonical_identity_review_case_events
    ADD CONSTRAINT canonical_identity_review_case_events_event_type_check
    CHECK (event_type IN (
        'AUTOMATED_RECOMMENDATION',
        'AUTOMATED_CONFIRMED',
        'AUTOMATED_REJECTED',
        'AUTOMATED_DEFERRED',
        'HUMAN_CONFIRMED',
        'HUMAN_REJECTED',
        'MORE_EVIDENCE_REQUIRED',
        'DEFERRED'
    )),
    ADD CONSTRAINT canonical_identity_review_case_events_reviewer_policy_check
    CHECK (
        (
            event_type IN (
                'AUTOMATED_RECOMMENDATION',
                'AUTOMATED_CONFIRMED',
                'AUTOMATED_REJECTED',
                'AUTOMATED_DEFERRED'
            )
            AND reviewer_type = 'AUTOMATED_SYSTEM'
        )
        OR
        (
            event_type IN (
                'HUMAN_CONFIRMED',
                'HUMAN_REJECTED',
                'MORE_EVIDENCE_REQUIRED',
                'DEFERRED'
            )
            AND reviewer_type = 'HUMAN'
        )
    ),
    ADD CONSTRAINT canonical_identity_review_case_events_evidence_hash_required
    CHECK (
        event_type NOT IN (
            'HUMAN_CONFIRMED',
            'HUMAN_REJECTED',
            'AUTOMATED_CONFIRMED',
            'AUTOMATED_REJECTED',
            'AUTOMATED_DEFERRED'
        )
        OR evidence_sha256 IS NOT NULL
    ),
    ADD CONSTRAINT canonical_identity_review_case_events_automated_policy_metadata
    CHECK (
        (
            event_type IN (
                'AUTOMATED_CONFIRMED',
                'AUTOMATED_REJECTED',
                'AUTOMATED_DEFERRED'
            )
            AND policy_version IS NOT NULL
            AND length(btrim(policy_version)) > 0
            AND confidence IS NOT NULL
            AND confidence >= 0.0
            AND confidence <= 1.0
            AND decision_basis IS NOT NULL
            AND length(btrim(decision_basis)) > 0
        )
        OR
        (
            event_type NOT IN (
                'AUTOMATED_CONFIRMED',
                'AUTOMATED_REJECTED',
                'AUTOMATED_DEFERRED'
            )
            AND policy_version IS NULL
            AND confidence IS NULL
            AND decision_basis IS NULL
        )
    );

CREATE OR REPLACE VIEW veltrix_ai_analyst.effective_canonical_identity_review_cases AS
SELECT
    review_case.*,
    COALESCE(latest.event_type, 'MORE_EVIDENCE_REQUIRED') AS latest_event_type,
    latest.reviewer_type AS latest_reviewer_type,
    latest.reviewer_id AS latest_reviewer_id,
    latest.reviewed_at AS latest_reviewed_at,
    latest.evidence_uri AS latest_evidence_uri,
    latest.notes AS latest_notes,
    CASE
        WHEN latest.event_type IN ('HUMAN_CONFIRMED', 'AUTOMATED_CONFIRMED')
            THEN latest.event_type
        WHEN latest.event_type IN ('HUMAN_REJECTED', 'AUTOMATED_REJECTED')
            THEN latest.event_type
        WHEN latest.event_type IN ('DEFERRED', 'AUTOMATED_DEFERRED')
            THEN latest.event_type
        WHEN latest.event_type = 'MORE_EVIDENCE_REQUIRED'
            THEN 'MORE_EVIDENCE_REQUIRED'
        ELSE 'HUMAN_REVIEW_REQUIRED'
    END AS effective_case_status,
    latest.policy_version AS latest_policy_version,
    latest.confidence AS latest_confidence,
    latest.decision_basis AS latest_decision_basis,
    CASE
        WHEN latest.event_type IN (
            'HUMAN_CONFIRMED',
            'HUMAN_REJECTED',
            'DEFERRED',
            'AUTOMATED_CONFIRMED',
            'AUTOMATED_REJECTED',
            'AUTOMATED_DEFERRED'
        ) THEN FALSE
        ELSE review_case.human_review_required
    END AS effective_human_review_required
FROM veltrix_ai_analyst.canonical_identity_review_cases review_case
LEFT JOIN LATERAL (
    SELECT
        event_type,
        reviewer_type,
        reviewer_id,
        reviewed_at,
        evidence_uri,
        notes,
        policy_version,
        confidence,
        decision_basis
    FROM veltrix_ai_analyst.canonical_identity_review_case_events event
    WHERE event.case_id = review_case.id
    ORDER BY event.reviewed_at DESC, event.id DESC
    LIMIT 1
) latest ON TRUE;

-- The England duplicate candidate is kept as two immutable source rows.
INSERT INTO veltrix_ai_analyst.canonical_identity_review_cases (
    case_key,
    case_type,
    primary_fixture_source_link_id,
    related_fixture_source_link_id,
    recommended_action,
    evidence_uris,
    evidence_summary
)
SELECT
    'ENGLAND_PREMIER_LEAGUE_DUPLICATE_MAN_CITY_BRIGHTON_2026',
    'FIXTURE_DUPLICATE_CANDIDATE',
    finished_link.id,
    unknown_link.id,
    'EXCLUDE_UNKNOWN_DUPLICATE_FROM_SETTLED_LABELS_WITHOUT_DELETING_OR_MERGING_SOURCE_ROWS',
    ARRAY[
        'https://www.mancity.com/matchday/fixtures/mens/2026/premier-league/man-city-v-brighton-31-oct-2026'
    ],
    'Official Manchester City match record confirms one 31 October 2026 fixture, Manchester City 0-1 Brighton. The provider FINISHED row is at 15:00 UTC; the paired UNKNOWN row is one minute later with identical teams.'
FROM veltrix_ai_analyst.canonical_fixture_sources finished_link
JOIN veltrix_ai_analyst.canonical_fixture_sources unknown_link
  ON unknown_link.provider = finished_link.provider
 AND unknown_link.source_id = finished_link.source_id
WHERE finished_link.provider = '5DollarFootballAPI'
  AND finished_link.source_id = '5dollarfootballapi'
  AND finished_link.provider_fixture_id = '1990703256'
  AND unknown_link.provider_fixture_id = '475377468'
ON CONFLICT (case_key) DO NOTHING;

-- Upgrade the 20 active Brazil Série B provider-team links from source-local
-- verification to real-world verification using the full 380/380 CBF schedule
-- pairing audit. The América Mineiro alternate provider ID is deliberately not
-- merged or verified as a separate active club; it remains a conflict candidate.
INSERT INTO veltrix_ai_analyst.canonical_identity_review_events (
    team_identity_link_id,
    decision,
    reviewer_id,
    reviewed_at,
    evidence_uri,
    evidence_sha256,
    supersedes_event_id,
    notes
)
SELECT
    link.id,
    'REAL_WORLD_IDENTITY_VERIFIED',
    'VELTRIX_CBF_AUTOMATED_ADJUDICATION_V1',
    statement_timestamp(),
    'https://github.com/Nexora-Apparel/veltrix-ai-analyst/blob/main/docs/ledger/2026-11-19-automated-identity-adjudication.md',
    '04fa83e4338ca839760a4ad2e6d3e804bd191de6a60bc96ac7a7417aca8f38d1',
    latest.id,
    'Policy cbf-2026-identity-adjudication-v1: this active provider team ID appears in exactly 38 FINISHED fixtures (19 home, 19 away); all ordered home/away pairings reconcile to the official CBF 2026 Série B schedule (380/380). Provider ID and raw labels remain unchanged; no canonical merge.'
FROM veltrix_ai_analyst.provider_team_identity_links link
JOIN LATERAL (
    SELECT event.id, event.decision
    FROM veltrix_ai_analyst.canonical_identity_review_events event
    WHERE event.team_identity_link_id = link.id
    ORDER BY event.reviewed_at DESC, event.id DESC
    LIMIT 1
) latest ON TRUE
WHERE link.provider = '5DollarFootballAPI'
  AND link.source_id = '5dollarfootballapi'
  AND link.provider_team_id IN (
      '1102583842', '1446563615', '1548718709', '1620921678', '1657329649',
      '1684426968', '2016651568', '2434042650', '2651466053', '2672186301',
      '3007875643', '3126624865', '3219034225', '3250670103', '3324195045',
      '4227927162', '4267737771', '559667509', '744720326', '844813267'
  )
  AND latest.decision = 'SOURCE_IDENTITY_REVIEWED'
  AND NOT EXISTS (
      SELECT 1
      FROM veltrix_ai_analyst.canonical_identity_review_events existing
      WHERE existing.team_identity_link_id = link.id
        AND existing.decision = 'REAL_WORLD_IDENTITY_VERIFIED'
        AND existing.reviewer_id = 'VELTRIX_CBF_AUTOMATED_ADJUDICATION_V1'
  );

-- The alternate América Mineiro provider ID is a duplicate/alias candidate,
-- not an additional active Série B club. Preserve its source-local link but mark
-- the real-world crosswalk as conflicted; never merge it automatically.
INSERT INTO veltrix_ai_analyst.canonical_identity_review_events (
    team_identity_link_id,
    decision,
    reviewer_id,
    reviewed_at,
    evidence_uri,
    evidence_sha256,
    supersedes_event_id,
    notes
)
SELECT
    link.id,
    'CONFLICT',
    'VELTRIX_CBF_AUTOMATED_ADJUDICATION_V1',
    statement_timestamp(),
    'https://github.com/Nexora-Apparel/veltrix-ai-analyst/blob/main/docs/ledger/2026-11-19-automated-identity-adjudication.md',
    '04fa83e4338ca839760a4ad2e6d3e804bd191de6a60bc96ac7a7417aca8f38d1',
    latest.id,
    'Provider ID 3808811746 appears only in the UNKNOWN duplicate Goiás-América row and has zero FINISHED appearances; ID 1102583842 has 38 FINISHED appearances and matches the official CBF América-MG schedule. Preserve both source IDs; no alias merge.'
FROM veltrix_ai_analyst.provider_team_identity_links link
JOIN LATERAL (
    SELECT event.id, event.decision
    FROM veltrix_ai_analyst.canonical_identity_review_events event
    WHERE event.team_identity_link_id = link.id
    ORDER BY event.reviewed_at DESC, event.id DESC
    LIMIT 1
) latest ON TRUE
WHERE link.provider = '5DollarFootballAPI'
  AND link.source_id = '5dollarfootballapi'
  AND link.provider_team_id = '3808811746'
  AND latest.decision = 'SOURCE_IDENTITY_REVIEWED'
  AND NOT EXISTS (
      SELECT 1
      FROM veltrix_ai_analyst.canonical_identity_review_events existing
      WHERE existing.team_identity_link_id = link.id
        AND existing.decision = 'CONFLICT'
        AND existing.reviewer_id = 'VELTRIX_CBF_AUTOMATED_ADJUDICATION_V1'
  );

-- Confirm the Brazil Série B competition crosswalk against the official CBF
-- 2026 competition schedule, without asserting commercial or PIT eligibility.
INSERT INTO veltrix_ai_analyst.canonical_identity_review_events (
    competition_identity_link_id,
    decision,
    reviewer_id,
    reviewed_at,
    evidence_uri,
    evidence_sha256,
    supersedes_event_id,
    notes
)
SELECT
    link.id,
    'REAL_WORLD_IDENTITY_VERIFIED',
    'VELTRIX_CBF_AUTOMATED_ADJUDICATION_V1',
    statement_timestamp(),
    'https://github.com/Nexora-Apparel/veltrix-ai-analyst/blob/main/docs/ledger/2026-11-19-automated-identity-adjudication.md',
    '04fa83e4338ca839760a4ad2e6d3e804bd191de6a60bc96ac7a7417aca8f38d1',
    latest.id,
    'Provider competition 522514093 is Brazil Série B 2026; official CBF schedule and the reconciled 380-fixture corpus confirm the competition and season context.'
FROM veltrix_ai_analyst.provider_competition_identity_links link
JOIN LATERAL (
    SELECT event.id, event.decision
    FROM veltrix_ai_analyst.canonical_identity_review_events event
    WHERE event.competition_identity_link_id = link.id
    ORDER BY event.reviewed_at DESC, event.id DESC
    LIMIT 1
) latest ON TRUE
WHERE link.provider = '5DollarFootballAPI'
  AND link.source_id = '5dollarfootballapi'
  AND link.provider_competition_id = '522514093'
  AND latest.decision = 'SOURCE_IDENTITY_REVIEWED'
  AND NOT EXISTS (
      SELECT 1
      FROM veltrix_ai_analyst.canonical_identity_review_events existing
      WHERE existing.competition_identity_link_id = link.id
        AND existing.decision = 'REAL_WORLD_IDENTITY_VERIFIED'
        AND existing.reviewer_id = 'VELTRIX_CBF_AUTOMATED_ADJUDICATION_V1'
  );

-- Record policy-versioned automated dispositions for the 28 existing cases
-- and the newly created England duplicate case. A deferred PIT case is closed
-- to human action only because its affected history is explicitly excluded.
WITH decisions AS (
    SELECT
        'BRAZIL_SERIE_B_RUN_3_TEAM_IDENTITY_' || link.provider_team_id AS case_key,
        'AUTOMATED_CONFIRMED'::text AS event_type,
        0.9950::numeric AS confidence,
        'CBF_380_FIXTURE_GRAPH_19_HOME_19_AWAY_MATCHED'::text AS decision_basis,
        'Active provider team ID ' || link.provider_team_id ||
        ' appears in 38 FINISHED fixtures (19 home, 19 away); the complete ordered fixture graph matches the official CBF schedule. This verifies the real-world club crosswalk but does not merge aliases or rewrite provider labels.'::text AS notes
    FROM veltrix_ai_analyst.provider_team_identity_links link
    WHERE link.provider = '5DollarFootballAPI'
      AND link.source_id = '5dollarfootballapi'
      AND link.provider_team_id IN (
          '1102583842', '1446563615', '1548718709', '1620921678', '1657329649',
          '1684426968', '2016651568', '2434042650', '2651466053', '2672186301',
          '3007875643', '3126624865', '3219034225', '3250670103', '3324195045',
          '4227927162', '4267737771', '559667509', '744720326', '844813267'
      )
    UNION ALL
    SELECT
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_AMERICA_MG',
        'AUTOMATED_CONFIRMED', 0.9950,
        'OFFICIAL_CBF_MATCH_AND_ONE_MINUTE_UNKNOWN_DUPLICATE',
        'CBF confirms one Goiás 3-1 América match on 22 March 2026. The FINISHED provider row is retained and the UNKNOWN row is flagged CONFLICT; both source rows remain immutable.'
    UNION ALL
    SELECT
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_FORTALEZA_LONDRINA',
        'AUTOMATED_CONFIRMED', 0.9950,
        'OFFICIAL_CBF_MATCH_AND_STALE_UNKNOWN_DATE',
        'CBF confirms Fortaleza 3-0 Londrina on 23 May 2026. The matching FINISHED row is retained and the August UNKNOWN row is flagged CONFLICT; no source row is deleted.'
    UNION ALL
    SELECT
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_FORTALEZA_BOTAFOGO',
        'AUTOMATED_CONFIRMED', 0.9950,
        'OFFICIAL_CBF_MATCH_AND_STALE_UNKNOWN_DATE',
        'CBF confirms Fortaleza 1-0 Botafogo on 28 July 2026. The matching FINISHED row is retained and the August UNKNOWN row is flagged CONFLICT; no source row is deleted.'
    UNION ALL
    SELECT
        'BRAZIL_SERIE_B_RUN_3_DUPLICATE_CEARA_LONDRINA',
        'AUTOMATED_CONFIRMED', 0.9950,
        'OFFICIAL_CBF_MATCH_AND_STALE_UNKNOWN_DATE',
        'CBF confirms Ceará 2-1 Londrina on 22 August 2026. The matching FINISHED row is retained and the 20 August UNKNOWN row is flagged CONFLICT; no source row is deleted.'
    UNION ALL
    SELECT
        'BRAZIL_SERIE_B_RUN_3_TEAM_ALIAS_AMERICA_MG',
        'AUTOMATED_CONFIRMED', 0.9900,
        'ALTERNATE_PROVIDER_ID_ONLY_ON_UNKNOWN_DUPLICATE',
        'The alternate América Mineiro provider ID appears only on the UNKNOWN duplicate Goiás fixture and has zero FINISHED appearances. The primary America MG ID matches the CBF club. Preserve both IDs; no canonical merge.'
    UNION ALL
    SELECT
        'BRAZIL_SERIE_B_RUN_3_COMPETITION_IDENTITY_522514093',
        'AUTOMATED_CONFIRMED', 0.9950,
        'OFFICIAL_CBF_COMPETITION_AND_SEASON_SCHEDULE',
        'Provider competition 522514093 is Brazil Série B 2026, confirmed against the official CBF schedule and reconciled fixture corpus.'
    UNION ALL
    SELECT
        'BRAZIL_SERIE_B_RUN_3_COVERAGE_2026',
        'AUTOMATED_CONFIRMED', 0.9900,
        '370_RUN3_FIXTURES_RECONCILED_TO_ROUNDS_1_TO_37',
        'The run-3 interval contains 370 FINISHED fixtures through 9 November 2026, corresponding to rounds 1-37; the full 380-fixture season schedule and scores reconcile to CBF. Round 38 is outside the run-3 window. This is coverage confirmation, not PIT certification.'
    UNION ALL
    SELECT
        'BRAZIL_SERIE_B_RUN_3_PIT_TIMESTAMP_GAP',
        'AUTOMATED_DEFERRED', 1.0000,
        'HISTORICAL_SOURCE_AVAILABILITY_TIMESTAMPS_ABSENT',
        'No verified source_published_at or available_at timestamps exist for the historical observations. Keep the affected history out of PIT-certified pre-match features; do not fabricate timestamps. Future prospective captures remain eligible under strict cutoff checks.'
    UNION ALL
    SELECT
        'ENGLAND_PREMIER_LEAGUE_DUPLICATE_MAN_CITY_BRIGHTON_2026',
        'AUTOMATED_CONFIRMED', 0.9950,
        'OFFICIAL_CLUB_MATCH_RECORD_AND_ONE_MINUTE_UNKNOWN_DUPLICATE',
        'The official Manchester City match record confirms one 31 October 2026 match, 0-1 to Brighton. The 15:00 FINISHED row is retained; the 15:01 UNKNOWN row remains CONFLICT and excluded from settled labels.'
)
INSERT INTO veltrix_ai_analyst.canonical_identity_review_case_events (
    case_id,
    event_type,
    reviewer_type,
    reviewer_id,
    reviewed_at,
    evidence_uri,
    evidence_sha256,
    notes,
    policy_version,
    confidence,
    decision_basis
)
SELECT
    review_case.id,
    decisions.event_type,
    'AUTOMATED_SYSTEM',
    'VELTRIX_CBF_AUTOMATED_ADJUDICATION_V1',
    statement_timestamp(),
    'https://github.com/Nexora-Apparel/veltrix-ai-analyst/blob/main/docs/ledger/2026-11-19-automated-identity-adjudication.md',
    '04fa83e4338ca839760a4ad2e6d3e804bd191de6a60bc96ac7a7417aca8f38d1',
    decisions.notes,
    'cbf-2026-identity-adjudication-v1',
    decisions.confidence,
    decisions.decision_basis
FROM decisions
JOIN veltrix_ai_analyst.canonical_identity_review_cases review_case
  ON review_case.case_key = decisions.case_key
WHERE NOT EXISTS (
    SELECT 1
    FROM veltrix_ai_analyst.canonical_identity_review_case_events existing
    WHERE existing.case_id = review_case.id
      AND existing.event_type = decisions.event_type
      AND existing.reviewer_id = 'VELTRIX_CBF_AUTOMATED_ADJUDICATION_V1'
)
ON CONFLICT (case_id, event_type, reviewer_id) DO NOTHING;
