# Six-competition historical corpus audit — 2026-11-18

## Scope and method

Read-only audit of the six 5DollarFootballAPI competition imports in Neon database veltrix_ai_analyst, import runs 6–11, exact competition IDs:

- Brazil Serie A: 3118717965 (run 6)
- England Premier League: 4160026622 (run 7)
- France Ligue 1: 3614399544 (run 8)
- Germany Bundesliga I: 686337048 (run 9)
- Italy Serie A: 3405541143 (run 10)
- Spain La Liga: 4212821298 (run 11)

No source rows, identities, or import metadata were modified. No provider requests or Odds API requests were made.

## Import-run integrity

| Competition | Run | Seen | Inserted | Duplicates | Rejected | Quarantined | Requests |
|---|---:|---:|---:|---:|---:|---:|---:|
| Brazil Serie A | 6 | 116 | 116 | 0 | 0 | 0 | 13 |
| England Premier League | 7 | 101 | 101 | 0 | 0 | 0 | 13 |
| France Ligue 1 | 8 | 91 | 91 | 0 | 0 | 0 | 13 |
| Germany Bundesliga I | 9 | 81 | 81 | 0 | 0 | 0 | 13 |
| Italy Serie A | 10 | 110 | 110 | 0 | 0 | 0 | 13 |
| Spain La Liga | 11 | 115 | 115 | 0 | 0 | 0 | 13 |
| **Total** | | **614** | **614** | **0** | **0** | **0** | **78** |

Run 6 was completed before the batch workflow; the batch skipped it as already validated. Runs 7–11 used 65 requests in the batch. The six import runs used 78 requests in aggregate. Each run status is COMPLETED and each run is scoped to its exact provider competition ID.

## Fixture and score audit

| Competition | Rows | FINISHED | Non-finished | Finished missing score | Repeated provider IDs | Outside import window |
|---|---:|---:|---:|---:|---:|---:|
| Brazil Serie A | 116 | 116 | 0 | 0 | 0 | 0 |
| England Premier League | 101 | 100 | 1 | 0 | 0 | 0 |
| France Ligue 1 | 91 | 90 | 1 | 0 | 0 | 0 |
| Germany Bundesliga I | 81 | 81 | 0 | 0 | 0 | 0 |
| Italy Serie A | 110 | 110 | 0 | 0 | 0 | 0 |
| Spain La Liga | 115 | 113 | 2 | 0 | 0 | 0 |
| **Total** | **614** | **610** | **4** | **0** | **0** | **0** |

All finished rows have both goals; no non-finished row has goals. All kickoff timestamps fall within the configured 2026-08-20 through 2026-11-18 import interval. No duplicate provider/source/provider-fixture keys exist.

The four non-finished rows are UNKNOWN and have no scores:
- Ligue 1: PSG–Rennes, provider fixture 4285540581, 2026-08-23 18:45 UTC.
- La Liga: Levante–Athletic Club, 660032673, 2026-09-16 19:30 UTC.
- La Liga: Rayo Vallecano–Athletic Club, 319329118, 2026-10-10 12:00 UTC.
- Premier League: Man City–Brighton, 475377468, 2026-10-31 15:01 UTC.

### Unresolved fixture duplicate/stale-row candidates

Two suspicious fixture pairs were found by comparing exact provider team IDs, kickoff proximity (within three minutes), and both home/away orientations:

**Ligue 1 — PSG/Rennes, same kickoff and reversed home/away orientation**
- 3279799888: Rennes–PSG, 18:45 UTC, FINISHED 2–2.
- 4285540581: PSG–Rennes, 18:45 UTC, UNKNOWN, no score.

**Premier League — Man City/Brighton, one-minute kickoff difference**
- 1990703256: Man City–Brighton, 15:00 UTC, FINISHED 0–1.
- 475377468: Man City–Brighton, 15:01 UTC, UNKNOWN, no score.

These are duplicate/stale-row candidates, not proven duplicates. Preserve all four source records. The two UNKNOWN rows are excluded from labeled training because they have no result. Do not merge, delete, or relabel any row without independent fixture evidence and human review.

## Team identity audit

- The six competitions contain 137 provider team catalogue IDs across the source.
- Every fixture has non-null home/away provider team IDs and names.
- One provider team ID in La Liga (2308376387) appears with two source labels: Deportivo A Coruna and Deportivo La Coruna. This is a source-label variation under the same provider ID, not evidence for merging different provider IDs. Preserve both observed labels in provenance; use the stable provider ID as the training identity key.
- No cross-competition provider team ID reuse was found in these six competition fixture rows.
- No canonical team or fixture mappings were created for these six imports. All 614 fixture rows are currently unlinked from canonical_fixture_sources. Do not claim canonical reconciliation is complete.

## Source provenance and point-in-time status

For all 614 fixture rows:
- Source observation exists and is linked to a provider response.
- Provider response returned HTTP 2xx.
- A latest observation sighting exists.
- Observation and sighting payload hashes match and are valid SHA-256 values.
- All observations use availability basis RETRIEVED_AT_ONLY.
- All 614 are point_in_time_certifiable = false.
- None has verified source publication time or point-in-time availability time.

All six competitions' observations were retrieved during the historical import on 2026-11-18, after their match kickoffs. Therefore these are **retrospective outcome records**, not historically point-in-time-certified pre-match features. Migration 010's prospective SYSTEM_OBSERVED_AT support does not retroactively certify these rows.

The source approval approval-5dollar-community-fixtures-2026-11-12 is APPROVED for collection, storage, historical import, internal analysis, feature engineering, model training, model validation and benchmarking; commercial use and raw redistribution are false. This audit used no raw-data redistribution.

## Training-data boundary

A retrospective event-time development dataset may use only the 610 FINISHED rows, with:
- Fixture key: provider fixture ID scoped by provider/source.
- Team keys: exact provider-local team IDs; no guessed aliases.
- Competition key: exact provider competition ID.
- Labels: observed final goals.
- Temporal split: strict kickoff-time expanding windows; simultaneous kickoff groups remain in the same fold.
- Unknown/non-finished rows: excluded from supervised score training but retained in source records and audit.
- PIT features: none from this corpus. Do not replay post-match retrieved observations as pre-match features.

This permits a retrospective outcome-only development experiment. It does not permit a PIT-certified evaluation or production promotion. The four unknown rows and both duplicate/stale-row candidates remain visible audit exclusions/risks.

## Existing identity-review queue

The existing 28 open review cases in the database concern the earlier Brazil Serie B corpus (competition ID 522514093), not these six newly imported competitions. They include 20 real-world team identity candidates, four fixture duplicate candidates, one team alias candidate, one competition identity candidate and two other case types (PIT timestamp gap and season coverage). They must not be conflated with the new six-competition audit.

## Next actions

1. Preserve the source-local identity namespace and create evidence-backed review cases for both the PSG–Rennes and Man City–Brighton duplicate candidates, plus the Deportivo label variation if the review-case workflow supports these case types without implying an alias.
2. Build an isolated, read-only six-competition retrospective dataset from the 610 finished rows.
3. Run chronological hierarchical Poisson hyperparameter tuning and estimate Dixon–Coles rho only from out-of-fold development forecasts.
4. Compare held-out forecasts against an independent competition-only baseline on exactly the same fixtures using Brier score, log loss and scoreline likelihood.
5. Publish the report as research-only. Do not write canonical mappings, update source records, or promote a production model as part of this workflow.
