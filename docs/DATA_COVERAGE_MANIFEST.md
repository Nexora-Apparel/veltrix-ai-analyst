# Historical Data Coverage Manifest Specification

**Document ID:** VAA-DATA-002  
**Version:** 1.0  
**Date:** 2026-11-16  
**Stage:** 2 — Data integrations and historical migration  
**Status:** Specification with a completed, bounded 5Dollar account/Brazil competition preflight and a verified AI Midas descriptive snapshot; no historical 5Dollar import or model-eligible coverage is certified.

## 1. Purpose

Define a reproducible, competition-level and field-level inventory of historical data available to VELTRIX AI ANALYST. The manifest is a decision input for ingestion planning and later model eligibility. It is not a prediction dataset and must not imply coverage where the source has not been queried and verified.

## 2. Required grain

One manifest record represents one provider × competition × season × data-field family × date interval. Split records whenever any of those dimensions has materially different coverage, timestamp semantics, rights, or quality.

Required dimensions:

- Provider identity and provider-local competition ID.
- Canonical competition identity only when a reviewed crosswalk exists.
- Season and inclusive/exclusive date boundaries, with timezone.
- Field family and individual field names.
- Expected, observed, missing, rejected, and quarantined counts where measurable.
- Earliest/latest event time and retrieval time.
- Source publication/availability timestamp coverage, separately from event timestamps.
- Rights approval ID, permitted use, commercial restriction, attribution, and raw redistribution policy.
- Request count, page count, response status, rate-limit observations, and collection window.
- Raw snapshot SHA-256, source revision/pin, schema version, and collector version.
- Quality flags, qualification state, and evidence links.

## 3. Coverage status vocabulary

| Status | Meaning |
|---|---|
| NOT_CHECKED | No fresh bounded verification has been run for this exact scope. |
| DISCOVERED | Competition or field is listed by the source; usable records not yet proven. |
| SAMPLED | A bounded sample was retrieved and inspected; no full coverage claim. |
| VERIFIED | Coverage and field semantics were measured over the stated interval with reproducible evidence. |
| RESTRICTED | Data exists but rights, timestamps, quality, or field semantics prevent the intended use. |
| UNAVAILABLE | The provider explicitly does not expose the requested scope/field. |
| FAILED | Verification could not complete due to an error; retain failure evidence. |

Do not use a single global “provider ready” flag. Qualification is per competition, field, interval, and intended use.

## 4. Timestamp classes

- EVENT_TIME: when the match/event occurred.
- SOURCE_PUBLISHED_AT: when the source made the record available.
- RETRIEVED_AT: when this system acquired the record.
- QUOTE_OBSERVED_AT: bookmaker quote timestamp, including timezone and bookmaker/market/line identity.
- UNKNOWN: timestamp semantics are absent or unverified.

Retrieval time must never be substituted for source publication time. Event time must never be treated as proof that a statistic was available before kickoff. Post-match statistics without a verified availability timeline are descriptive-only and excluded from pre-match features.

## 5. Intended-use gates

| Intended use | Minimum evidence |
|---|---|
| Fixture scheduling/results | Stable source IDs, timezone-aware kickoff, settled-score semantics, provenance, deduplication. |
| Historical descriptive analysis | Verified rows/schema, rights approval, source pin/checksum, anomaly handling. |
| Pre-match feature | Verified feature availability strictly before the forecast cutoff; no post-match leakage. |
| Model training/evaluation | PIT eligibility, chronological split safety, source/rights traceability, stable identities, quality review. |
| Odds/value/CLV | Bookmaker, market, line, quote price, timezone-aware observed timestamp, opening/closing semantics, sufficient timestamp coverage. |
| Public display | Applicable attribution, licence/terms, field restrictions, privacy and redistribution checks. |

## 6. Initial source records (known evidence, not fresh qualification)

### AI Midas — Brazil Série B 2026

- Source: `aimidas1/aimidas1`, pinned commit `29baca362a34ce5dcd3924b07ec9c7d5139d83fc`.
- File: `advanced stats/Brazil Serie B 2026.csv`.
- Expected raw bytes: 192,284; 738 team-match rows; 369 matches; 20 teams; dates 2026-03-21 to 2026-11-08.
- Capture executed in GitHub Actions run [#43882958891](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43882958891); raw bytes 192,284; SHA-256 `55b0c00629abd2d4ff3c31659ada950b67ffc2752609284b32c15c99f71152ab`; Git blob SHA-1 `b6bdb94c053d2149e6232fb100e1f158e46e4533`.
- One match (Náutico 0-3 CRB, 2026-11-07) is quarantined for inconsistent team-row scores; 368 other matches are descriptive-data candidates, not pre-match features.
- Rights: non-commercial only; attribution required; raw redistribution prohibited.
- Timestamp class: EVENT_TIME plus RETRIEVED_AT only; SOURCE_PUBLISHED_AT unavailable.
- Eligibility: historical descriptive/reconciliation only until a pre-match availability timeline is independently established. Not PIT-certified; not eligible as pre-match model features.
- Odds: this file contains no odds fields. Other AI Midas average-odds records are not bookmaker/timestamp qualified.

### 5DollarFootballAPI — Community

- New-repository secret `FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY` was consumed by the manual verification workflow; no credential value was printed.
- Run [#43884649616](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43884649616), completed successfully on 2026-11-16.
- Account plan: `community`; reported limits: 300 requests/hour, 20-request/minute burst; reported `usage.today`: 0 at the time returned by the status endpoint.
- Brazil competition listing: 2 entries; Brazil Serie B visible as provider competition ID `522514093`.
- This proves account and competition-list visibility only. It does not prove fixture/result endpoint access, season/date coverage, field completeness, or historical completeness.
- Prior 365-day qualification in the legacy environment: 2,496 finished fixtures, 26 pages, 28 requests under a 40-request cap, no duplicates/rejections. Do not repeat this full pull merely to reconfirm access.
- Historical odds ticks: prior Community endpoint returned HTTP 403 and sampled timestamp coverage was inadequate; not qualified for CLV.

## 7. Cross-provider identity rules

- Preserve provider-local IDs and raw names.
- A canonical competition/team/fixture ID requires an explicit reviewed crosswalk with evidence.
- Never join fixtures on names alone where ambiguity exists.
- Candidate matching may use normalized teams, competition, kickoff interval and season, but ambiguous or conflicting pairs must be quarantined.
- Record match confidence and the evidence supporting each crosswalk; never silently merge.

## 8. Collection and quota controls

- Every collection run must declare an explicit request ceiling, date interval, page ceiling, and maximum response bytes before execution.
- Use bounded date windows, pagination checkpoints, response caching, deduplication and resumable watermarks.
- Persist request events and failures without logging credentials or sensitive headers.
- Stop on 401/403, unexpected plan/entitlement, schema drift, repeated 429, unexpected page growth, or budget exhaustion.
- No bulk history pull, odds expansion, paid call, database provisioning, or import is authorised by this specification.

## 9. Exit criteria for a verified coverage record

A record may be marked VERIFIED only when:
1. The exact source/competition/season/field scope is identified.
2. Rights approval covers the intended use and retention.
3. The date interval and pagination are complete or explicitly bounded.
4. Raw response/snapshot checksums and schema version are retained privately.
5. Counts, missingness, duplicate rate, invalid rows and anomaly/quarantine counts are reported.
6. Event and source-availability timestamp semantics are independently established.
7. Any cross-provider mapping is reviewed and ambiguity is quarantined.
8. The actual request count and quota impact are recorded.

A VERIFIED coverage record may still be RESTRICTED for pre-match modelling, odds/CLV, or public display. Coverage and intended-use eligibility are separate decisions.

## 10. Next execution

1. Design a strictly bounded 5Dollar Brazil Serie B fixture/result endpoint probe to establish actual endpoint access and response schema; do not start a season backfill.
2. Populate measured competition/field/date records from bounded evidence; do not infer missing values.
3. Define the historical request budget and resumable import plan from measured pagination and quota evidence.


## 11. Bounded 5Dollar fixture probe — prepared, not executed

- Implementation: `scripts/probe_5dollar_brazil_fixtures.py`; workflow: `.github/workflows/5dollar-fixture-probe.yml`.
- Scope: Brazil Serie B provider ID `522514093`; `GET /v1/leagues/522514093/fixtures`; 2026-11-07T00:00:00Z inclusive to 2026-11-09T00:00:00Z exclusive; page 1 only; page size 100.
- Hard ceiling: one HTTP request, zero retries, zero pagination follow-ups. No odds calls and no database writes.
- Output: sanitized manifest with HTTP status, response SHA-256/bytes, schema keys, first-page pagination and first-fixture timestamp candidates. Raw response and API key are not printed or uploaded.
- Status: PREPARED; not executed. Fixture/result endpoint access, returned fields, timestamp semantics and date coverage remain NOT_CHECKED.
- Manual workflow dispatch is required; see `docs/ledger/2026-11-16-5dollar-fixture-probe-prepared.md`. The existing Community secret is already configured.
