# Historical Data Coverage Manifest Specification

**Document ID:** VAA-DATA-002  
**Version:** 1.1  
**Date:** 2026-11-16  
**Stage:** 2 — Data integrations and historical migration  
**Status:** AI Midas descriptive snapshot verified; 5Dollar Brazil Serie B fixture endpoint sampled successfully over one bounded two-day interval. No season-wide historical coverage or model eligibility is certified.

## 1. Purpose

Define a reproducible, competition-level and field-level inventory of historical data available to VELTRIX AI ANALYST. This manifest is a decision input for ingestion planning and later model eligibility. It must not imply coverage where the source has not been queried and verified.

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

## 6. Initial source records

### AI Midas — Brazil Série B 2026

- Source: `aimidas1/aimidas1`, pinned commit `29baca362a34ce5dcd3924b07ec9c7d5139d83fc`.
- File: `advanced stats/Brazil Serie B 2026.csv`.
- 192,284 bytes; 738 team-match rows; 369 matches; 20 teams; dates 2026-03-21 to 2026-11-08.
- Capture: [GitHub Actions run #43882958891](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43882958891); SHA-256 `55b0c00629abd2d4ff3c31659ada950b67ffc2752609284b32c15c99f71152ab`; Git blob SHA-1 `b6bdb94c053d2149e6232fb100e1f158e46e4533`.
- One match (Náutico 0–3 CRB, 2026-11-07) quarantined for inconsistent team-row scores; 368 matches remain descriptive-data candidates.
- Rights: non-commercial only; attribution required; raw redistribution prohibited.
- Timestamp class: EVENT_TIME and RETRIEVED_AT only; SOURCE_PUBLISHED_AT unavailable.
- Eligibility: descriptive/reconciliation only; not PIT-certified or eligible as pre-match model features.
- No odds fields in this file. Other AI Midas average-odds records are not bookmaker/timestamp qualified.

### 5DollarFootballAPI — Community account and competition catalogue

- Secret `FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY` consumed through GitHub Actions; credential value was not printed.
- Run [#43884649616](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43884649616) succeeded on 2026-11-16.
- Account plan: `community`; reported limits: 300 requests/hour and 20/minute burst.
- Brazil competition listing: two entries; Brazil Serie B visible as provider competition ID `522514093`.
- This proves account and competition-list visibility only.

### 5DollarFootballAPI — Brazil Serie B fixture endpoint sample

- Run [#43916841159](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43916841159) succeeded on 2026-11-16.
- Endpoint: `GET /v1/leagues/522514093/fixtures`.
- Window: `[2026-11-07T00:00:00Z, 2026-11-09T00:00:00Z)`; page 1; page size 100.
- Actual request budget: one HTTP request; zero retries; zero pagination follow-ups; no odds request; no database write.
- HTTP 200; 8 rows; pagination count 8; `has_more=false`; response size 3,872 bytes.
- Response SHA-256: `76009f299a3d4a42e9df54d8d9cf6682a43b7e3f36c12713a7cc940d41fc88d8`.
- Field union observed: `cards`, `corners`, `goals`, `id`, `kickoff_ts`, `kickoff_utc`, `league`, `status`, `status_code`, `status_reason`, `teams`.
- First fixture sample: ID 3728617699; kickoff `2026-11-08T22:15:00+00:00`; status `finished`.
- Timestamp evidence: kickoff/event-time fields were observed. No SOURCE_PUBLISHED_AT or record-availability timestamp was established.
- Sanitized manifest artifact: `5dollar-brazil-serie-b-fixture-probe`, artifact ID 14250910940, 704 bytes, retained for 7 days. Raw response and API key were not uploaded.
- Qualification: **SAMPLED** for endpoint access and observed response schema in this exact two-day window. This does not establish season completeness, historical coverage, full result semantics, source publication timestamps, odds availability, PIT eligibility or model eligibility.
- Prior legacy-environment 365-day qualification: 2,496 finished fixtures, 26 pages, 28 requests under a 40-request cap, no duplicates/rejections. Do not repeat this full pull merely to reconfirm access.
- Prior Community historical odds tick endpoint returned HTTP 403; sampled timestamp coverage was inadequate. Not qualified for CLV.

## 7. Cross-provider identity rules

- Preserve provider-local IDs and raw names.
- A canonical competition/team/fixture ID requires an explicit reviewed crosswalk with evidence.
- Never join fixtures on names alone where ambiguity exists.
- Candidate matching may use normalized teams, competition, kickoff interval and season, but ambiguous or conflicting pairs must be quarantined.
- Record match confidence and supporting evidence; never silently merge.

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
8. Actual request count and quota impact are recorded.

A VERIFIED coverage record may still be RESTRICTED for pre-match modelling, odds/CLV, or public display. Coverage and intended-use eligibility are separate decisions.

## 10. Next execution

1. Inspect fixture/result field semantics and compare the observed response contract with the adapter implementation; use offline fixtures/tests and do not spend another provider request unnecessarily.
2. Design the historical request budget and resumable import plan from measured pagination and quota evidence.
3. Populate further measured competition/field/date records only from bounded evidence; do not infer missing values.
4. Provision a separate private PostgreSQL database only after the exact target and credentials are configured.
