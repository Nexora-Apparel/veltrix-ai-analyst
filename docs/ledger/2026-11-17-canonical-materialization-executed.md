# Canonical materialization executed and independently verified — 2026-11-17

## GitHub Actions execution

- Workflow run [#44086857898](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44086857898), job [#134051435015](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44086857898/job/134051435015), completed successfully.
- Checked-out main commit: `e6ca720ca556c5cb6aea7e867075e841b0f7bf3e`.
- Runner output status: `MATERIALIZATION_COMMITTED`; final marker: `CANONICAL_MATERIALIZATION_COMMITTED`.
- Database identity checked by runner: `veltrix_ai_analyst`.
- Workflow steps: checkout, Python setup, runner installation, and “Materialize pinned Brazil Serie B run 3” all completed successfully.

## Transaction report

Scope: provider `5DollarFootballAPI`, source `5dollarfootballapi`, Brazil Serie B competition `522514093`, import run 3.

| Table | Before | After |
|---|---:|---:|
| canonical_teams | 0 | 21 |
| canonical_competitions | 0 | 1 |
| canonical_fixtures | 0 | 374 |
| provider_team_identity_links | 0 | 21 |
| provider_competition_identity_links | 0 | 1 |
| canonical_fixture_sources | 0 | 374 |
| canonical_identity_review_events | 0 | 0 |

Runner result:
- 21 teams created; one competition created; 374 fixtures created; zero fixtures reused.
- Zero identity review events created.
- Zero PIT observations promoted.
- Zero provider requests made.
- 370 FINISHED fixtures; four UNKNOWN fixtures.
- Conflict fixture IDs: `2341822348`, `3116209225`.
- Planner reported ready with zero blockers; 396 source observations remain non-PIT.

## Independent read-only Neon verification

Project/resource: `young-wind-27772160`; database: `veltrix_ai_analyst`.

A separate read-only SQL query independently confirmed:
- 21 canonical teams.
- One canonical competition.
- 374 canonical fixtures.
- 21 provider team identity links.
- One provider competition identity link.
- 374 canonical fixture-source links.
- Zero canonical identity review events.
- Zero `pre_match_feature_observations`.

A second read-only grouped status query confirmed:
- Team identity links: 21 `REVIEW_REQUIRED`.
- Competition identity links: one `REVIEW_REQUIRED`.
- Fixture-source links: 374 `REVIEW_REQUIRED`.
- Canonical fixture completeness: 374 `SOURCE_ROW_ONLY`.
- Fixture identity: two `CONFLICT`, 372 `IDENTITY_REVIEW_REQUIRED`.
- Fixture status: 370 `FINISHED`, four `UNKNOWN`.

A source audit confirmed 374 fixture/result source observations and 374 linked sightings, with zero PIT-certifiable observations and zero PIT-certifiable sightings.

## Interpretation and release boundary

This is a successful, atomic source-row canonical materialization, not a certification of real-world team identity, season completeness, source publication timestamps, pre-match feature eligibility, or model readiness.

- Keep all provider identity links in `REVIEW_REQUIRED` until independently evidenced human review.
- Preserve the two fixture conflict flags; do not merge either record automatically.
- Keep all canonical fixtures `SOURCE_ROW_ONLY`.
- Do not use the 396 non-PIT observations or these source-row-only entities as pre-match model features.
- No model training, calibration, prediction publication, or production prediction API is authorized by this step.
- Android runtime testing and typed backend integration remain deferred until the appropriate later stage and real prediction endpoints exist.

## Next stage

Proceed to evidence-backed identity review and source/season coverage reconciliation. Build a review queue with immutable evidence references and explicit reviewer decisions; do not mutate identity mappings merely to remove unresolved states. In parallel, establish what additional rights-approved, timestamp-qualified data is needed before point-in-time feature engineering can begin.
