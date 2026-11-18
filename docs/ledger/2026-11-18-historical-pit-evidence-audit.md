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

The current production corpus has no source-publication or system-availability timestamp on its 384 sightings. It therefore remains excluded from point-in-time-certified pre-match feature inputs. The successful historical import integration test now verifies that future retrieval events can be stored with their system-observed retrieval time without falsely promoting those observations to PIT-certified evidence.

## What this audit does not establish

A historical observation collected after kickoff cannot be made point-in-time safe by backfilling its retrieval time or by obtaining the final CBF schedule. The old corpus remains non-PIT.

A future prospective snapshot process must:
1. Persist immutable raw provider response bytes and checksums.
2. Record the exact retrieval timestamp for every response and normalized observation.
3. Link each observation to the exact provider response and source sighting.
4. Capture the fixture's official kickoff separately.
5. Admit a feature to a historical pre-match replay only when the evidence shows that the snapshot was retrieved before the fixture kickoff and its contents were available at that time.
6. Keep provider publication time distinct from system retrieval time; never label retrieval time as provider publication time.
7. Require explicit source rights for the data type and permitted research/model uses.
8. Preserve the snapshot and evidence append-only.

## Validation status

- Historical PIT certification: **BLOCKED**
- Retrospective prequential report: **research-only; not PIT-certified**
- Production model promotion: **not authorized**
- Value betting: **locked**
- No backfill or modification of existing source observations: **performed**
