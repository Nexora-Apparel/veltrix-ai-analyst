# Canonical entity schema implementation review — 2026-11-17

## Scope

Prepare Migration 007 for the canonical team, competition, fixture, provider identity-link and fixture-source layer. This is schema-only work. It does not materialize rows or modify provider data.

## Repository state

- Base: `main` at `c23dc52f8c267236aa1ccf0c9234ab85515054aa`.
- Work branch: `stage1/canonical-entity-schema-007-20261117`.
- Initial schema commit discovered on the existing branch: `d07478223511bb4a1079c2ae95dc7b53fbdc8a4e`.
- No open pull request existed when work resumed; draft PR [#14](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/14) was subsequently opened.
- Migration 007 and supporting tests/workflow/docs are still unmerged and have not been applied to Neon.

## Schema design

- Canonical team, competition and fixture tables are separate from immutable provider projections.
- Team and competition identity links bind exact provider-local IDs to exact provider projection rows, source observations, source sightings, successful response records, rights approvals and payload hashes.
- Fixture source links bind an exact provider fixture row and exact provenance to one canonical fixture.
- Provider links and review events are append-only.
- New identity links begin in `REVIEW_REQUIRED`; a review decision must be recorded as an append-only event with reviewer and evidence URI/hash.
- Supersession events must target the same identity link and have a later review timestamp.
- Canonical fixtures cannot be marked `VERIFIED` until source-fixture, competition, home-team and away-team links have explicit qualifying review events.
- A second source row cannot be attached to a canonical fixture without manual evidence and review of the existing source link.
- Provider IDs and source records are never rewritten. No fuzzy matching, accent folding or inferred real-world identity is allowed.

## Review hardening applied

- Removed direct insertion of pre-reviewed statuses from identity-link rows; review state is event-driven.
- Restricted canonical entity identity basis to source-local or unresolved. Real-world verification belongs in evidence-backed review events.
- Corrected multi-source guard logic to fail closed when any existing source link lacks the required review event.
- Corrected canonical fixture verification checks to fail closed when any required mapping is absent.

## Tests and workflow

- Extended migration integration assertions through migration 007.
- Added static canonical-schema contract tests.
- Extended the controlled migration workflow to verify checksums and required tables/functions/triggers for migrations 006 and 007.
- Extended workflow contract tests and the database migration runbook.
- PR CI run [#44064737019](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44064737019) was superseded/cancelled as the branch was hardened. The current head's CI is queued/running; results are not yet verified. PostgreSQL execution of migration 007 remains required.

## CI failure diagnosis and correction — 2026-11-17

- Run [#44065008513](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44065008513) failed in the backend test job; Android debug build succeeded and uploaded its APK.
- Backend result: 86 passed, 1 failed, 20 errors. The setup errors were downstream effects of Migration 007 failing to parse.
- PostgreSQL reported `syntax error at or near "$" at character 10874` in `guard_canonical_fixture_source_merge()`. The function delimiter had one dollar sign instead of the required paired `$`.
- Corrected the delimiter in commit `23a3ac026e703db6748c165cd5d0638b7c97c2d1`.
- Added a static regression assertion for the malformed delimiter in commit `ae670ffb1e4fb8ee4c091a79b657d074ba6c1bec`.
- This is a source-level correction only. The failing run used an ephemeral CI PostgreSQL service; no Neon schema was changed.
- Rerun CI is required. Migration 007 remains unvalidated until backend tests/lint and Android build pass, followed by controlled PostgreSQL verification.

## Data and safety disposition

- No provider HTTP requests.
- No Neon writes or migrations.
- No canonical entities or identity links materialized.
- No provider fixture rows changed.
- The 374 5Dollar Brazil Serie B observations remain non-PIT-certified and excluded from pre-match features.
- The four UNKNOWN fixtures remain scoreless.
- Provider IDs `1102583842` (`America MG`) and `3808811746` (`América Mineiro`) remain separate and unresolved.
- No model training, prediction API, prediction publication or Android backend integration.

## Next

1. Run full PR CI and correct every failure.
2. Review PostgreSQL migration behavior against an ephemeral database.
3. Open/complete PR review; do not merge if SQL checks fail.
4. After review and merge, use the controlled migration workflow against the exact `veltrix_ai_analyst` database and verify migration 007 checksum plus objects.
5. Only then begin the separate canonical materialization service and read-only reconciliation tests. Human review must not be fabricated.
