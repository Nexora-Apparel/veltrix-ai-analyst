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


## Final CI, review and merge result — 2026-11-17

- The latest pre-fix run [#44067281973](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44067281973) failed on commit `d9fb10bf8efe53ef62330d559b153f1188b76490`: PostgreSQL still found a single-dollar PL/pgSQL delimiter in `guard_canonical_fixture_source_merge()`. Backend result was 86 passed, 1 failed, 20 setup errors; Android build and APK artifact upload passed.
- Corrected the actual migration source in commit `3269ae69d315071dc09a227fed969f35e6af7c38`; the earlier ledger claim that the delimiter had been corrected was premature because the checked-out migration still contained the malformed delimiter.
- Added a delimiter regression test. Its first version had an assertion-string escaping error and failed run #44068347158 (106 passed, 1 failed). Corrected the test in commit `5f57a1afc869c7ea5f5f953269dcb33d6ae6ac7a`.
- Final CI [#44068513459](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44068513459) completed successfully on commit `5f57a1afc869c7ea5f5f953269dcb33d6ae6ac7a`: backend tests passed, Ruff lint passed, Android debug APK assembly passed, and APK artifact upload passed.
- Migration source review confirmed four paired PL/pgSQL function delimiters, no remaining malformed single-dollar opener, schema-only behavior, provenance-bound source links, append-only identity/review records, and fail-closed canonical fixture verification gates.
- PR [#14](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/14) was marked ready and squash-merged after successful CI. Merge commit: `759f2fa80b9c05551e278af7eb306760875a0063`.
- **Migration 007 is NOT yet applied to Neon.** No production database mutation, provider request, canonical row materialization, PIT promotion, or model operation was performed during this review/merge.
- Controlled migration workflow: [Apply checksum-verified database migrations](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/apply-database-migrations.yml). It is manual `workflow_dispatch` and requires `confirm_migrations=APPLY_CHECKSUM_VERIFIED_MIGRATIONS`; the workflow then verifies the exact migration-file SHA-256 against `public.schema_migrations` and checks the required Migration 006/007 tables, functions and triggers.
- The connected GitHub actions do not expose a workflow-dispatch write operation in this session. Therefore the manual dispatch is a logged blocker; do not bypass the controlled workflow by applying SQL directly. Migration checksum and Neon object verification remain pending until the workflow completes successfully.

## Materialization gate

Canonical materialization remains blocked until the controlled Migration 007 workflow reports success and its checksum/object verification is inspected. After that, materialization must use source-native placeholders and preserve unresolved mappings as `REVIEW_REQUIRED`; the America MG / América Mineiro pair must remain separate and flagged. No human review may be fabricated. The 374 imported observations remain non-PIT-certified and excluded from pre-match features.
