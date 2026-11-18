-- VELTRIX AI ANALYST — read-only historical corpus qualification audit
-- Target: Neon database veltrix_ai_analyst
-- Scope: 5DollarFootballAPI / 5dollarfootballapi / Brazil Serie B 522514093
-- Run only in a READ ONLY transaction. Every statement below is SELECT-only.
-- This audit does not reconcile official results or authorize identity changes.

-- 1. Provider fixture status and score completeness.
SELECT status,
       COUNT(*) AS fixture_rows,
       COUNT(*) FILTER (WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL) AS scored_rows
FROM veltrix_ai_analyst.provider_fixtures
WHERE provider = '5DollarFootballAPI'
  AND source_id = '5dollarfootballapi'
  AND provider_competition_id = '522514093'
GROUP BY status
ORDER BY status;

-- 2. Source observation provenance and PIT eligibility.
SELECT data_type,
       availability_basis,
       COUNT(*) AS observations,
       COUNT(*) FILTER (WHERE source_published_at IS NULL) AS missing_source_published_at,
       COUNT(*) FILTER (WHERE available_at IS NULL) AS missing_available_at,
       COUNT(*) FILTER (WHERE point_in_time_certifiable) AS pit_certifiable
FROM veltrix_ai_analyst.source_observations
WHERE provider = '5DollarFootballAPI'
  AND source_id = '5dollarfootballapi'
GROUP BY data_type, availability_basis
ORDER BY data_type, availability_basis;

-- 3. Fixture/result observation sightings and their independent PIT fields.
SELECT COUNT(*) AS sightings,
       COUNT(*) FILTER (WHERE s.source_published_at IS NULL) AS missing_source_published_at,
       COUNT(*) FILTER (WHERE s.available_at IS NULL) AS missing_available_at,
       COUNT(*) FILTER (WHERE s.point_in_time_certifiable) AS pit_certifiable
FROM veltrix_ai_analyst.source_observation_sightings AS s
JOIN veltrix_ai_analyst.source_observations AS o
  ON o.id = s.source_observation_id
WHERE o.provider = '5DollarFootballAPI'
  AND o.source_id = '5dollarfootballapi'
  AND o.data_type = 'fixtures_and_results';

-- 4. Canonical fixture identity and completeness state.
SELECT identity_status, completeness_status, COUNT(*) AS fixtures
FROM veltrix_ai_analyst.canonical_fixtures
GROUP BY identity_status, completeness_status
ORDER BY identity_status, completeness_status;

-- 5. Source provenance is distinct from effective human review status.
SELECT source_fixture_provenance_status, effective_review_status, COUNT(*) AS links
FROM veltrix_ai_analyst.canonical_fixture_source_provenance_audit
GROUP BY source_fixture_provenance_status, effective_review_status
ORDER BY source_fixture_provenance_status, effective_review_status;

SELECT source_identity_provenance_status, real_world_identity_status, COUNT(*) AS team_links
FROM veltrix_ai_analyst.canonical_team_identity_provenance_audit
GROUP BY source_identity_provenance_status, real_world_identity_status
ORDER BY source_identity_provenance_status, real_world_identity_status;

SELECT source_identity_provenance_status, real_world_identity_status, COUNT(*) AS competition_links
FROM veltrix_ai_analyst.canonical_competition_identity_provenance_audit
GROUP BY source_identity_provenance_status, real_world_identity_status
ORDER BY source_identity_provenance_status, real_world_identity_status;

-- 6. Outstanding human review case inventory.
SELECT case_type, COUNT(*) AS cases,
       COUNT(*) FILTER (WHERE human_review_required) AS requiring_human_review
FROM veltrix_ai_analyst.canonical_identity_review_cases
GROUP BY case_type
ORDER BY case_type;

-- 7. Exact duplicate-candidate evidence. These rows are preserved, not deleted.
SELECT case_key,
       primary_provider_fixture_id,
       duplicate_provider_fixture_id,
       primary_provider_kickoff_at,
       duplicate_provider_kickoff_at,
       primary_provider_status,
       duplicate_provider_status,
       home_goals,
       away_goals,
       recommended_action,
       evidence_summary
FROM veltrix_ai_analyst.canonical_fixture_duplicate_case_audit
ORDER BY case_key;

-- 8. Team alias candidate evidence. Do not merge without a human decision.
SELECT case_key,
       primary_provider_team_id,
       primary_provider_team_name,
       alias_provider_team_id,
       alias_provider_team_name,
       recommended_action,
       effective_case_status,
       evidence_summary
FROM veltrix_ai_analyst.canonical_team_alias_case_audit
ORDER BY case_key;

-- 9. Immutable provider-local team catalogue. IDs are not canonical real-world identities.
SELECT provider_team_id, name, country_code
FROM veltrix_ai_analyst.provider_teams
WHERE provider = '5DollarFootballAPI'
  AND source_id = '5dollarfootballapi'
ORDER BY name, provider_team_id;
