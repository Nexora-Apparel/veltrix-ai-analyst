# Historical point-in-time evidence audit — 2026-11-18

## Scope

Read-only audit of the production Neon corpus used for the CBF Série B 2026 retrospective research. No provider calls, writes, odds API credits, or source-row changes were made.

## Observed evidence counts

The query joins immutable 5DollarFootballAPI fixture observations to their observation-sighting records for competition `522514093`.

| Measure | Count |
|---|---:|
| Distinct source observations | 384 |
| Distinct retrieval sightings | 384 |
| Sightings with source publication timestamp | 0 |
| Sightings with `available_at` populated | 0 |
| Sightings marked `RETRIEVED_AT_ONLY` | 384 |
| Sightings marked PIT-certifiable | 0 |
| Observations with source publication timestamp | 0 |
| Observations with `available_at` populated | 0 |

The corpus consists of 380 FINISHED fixtures and four UNKNOWN observations retained for duplicate/stale-row review. The four UNKNOWN rows are not promoted into the labeled training set.

## Time semantics and decision

- `retrieved_at` records when the system collected a response.
- `available_at` is a distinct field representing when the observation is evidenced as available to the prediction system.
- `source_published_at` is the provider's publication/update timestamp, which is absent in these historical payloads.
- `RETRIEVED_AT_ONLY` does not assert a provider publication time.
- No retrospective timestamp is inferred from kickoff, result time, or current provider state.

The current production corpus has no source-publication or system-availability timestamp on its 384 sightings. It therefore remains excluded from point-in-time-certified pre-match feature inputs.

A prospective capture path is now implemented in code. It uses the separate `SYSTEM_OBSERVED_AT` basis only when the exact provider response has been captured and linked, `available_at = retrieved_at`, the response fetch timestamp equals the sighting retrieval timestamp, and the prediction cutoff is at or after that capture. It does not invent or claim a provider publication timestamp. Historical fixtures captured after kickoff remain `RETRIEVED_AT_ONLY` and non-PIT. The new integration test exercises the future-fixture path.

**Code verification:** [CI run 44288668318](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44288668318) passed on commit `dae564eca874b5b16385909a96ad904db60334ad`: 290 backend tests, Ruff lint and Android debug build. The integration suite verifies that system-observed evidence is rejected if the response fetch time differs from the sighting retrieval time or if the prediction cutoff precedes capture.

**Production status:** migration `010_system_observed_pit.sql` is committed and covered by CI, but is not yet applied to the production Neon database. The production `schema_migrations` ledger currently ends at migration 009. Until migration 010 is applied and verified through the checksum-gated migration workflow, the new basis is not active in production.

**Activation blocker:** the repository's `Apply checksum-verified database migrations` workflow is manual by design. It requires the explicit input `APPLY_CHECKSUM_VERIFIED_MIGRATIONS`. The workflow has been updated to verify migration 010's checksum, PIT constraints and trigger; it has not been dispatched from this session.

## What this audit does not establish

A historical observation collected after kickoff cannot be made point-in-time safe by backfilling its retrieval time or by obtaining the final CBF schedule. The old corpus remains non-PIT.

A future prospective snapshot process must:
1. Persist immutable raw provider response bytes and checksums.
2. Record the exact retrieval timestamp for every response and normalized observation.
3. Link each observation to the exact provider response and source sighting.
4. Capture the fixture's official kickoff separately.
5. Admit a feature to a historical pre-match replay only when the evidence shows that the snapshot was retrieved before the fixture kickoff and its contents were available at that time.
6. Keep provider publication time distinct from system retrieval time; never label retrieval time as provider publication time. When no publisher timestamp exists, use `SYSTEM_OBSERVED_AT` only for the exact response actually captured before the prediction cutoff.
7. Require the provider response's `fetched_at` to equal the sighting's `retrieved_at`, and require `available_at = retrieved_at` for system-observed evidence.
8. Require explicit source rights for the data type and permitted research/model uses.
9. Preserve the snapshot and evidence append-only.

## Validation status

- Historical PIT certification: **BLOCKED**
- Retrospective prequential report: **research-only; not PIT-certified**
- Production model promotion: **not authorized**
- Value betting: **locked**
- No backfill or modification of existing source observations: **performed**
