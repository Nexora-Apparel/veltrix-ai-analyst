# 5Dollar Brazil Serie B — bounded historical collection plan

**Document ID:** VAA-INGEST-PLAN-001  
**Version:** 1.0  
**Date:** 2026-11-16  
**Status:** DESIGN ONLY — not dispatched; no historical collection or database write is authorized by this plan.

## 1. Objective and strict scope

Prepare a resumable, quota-bounded fixture/result collection for one competition only:

- Provider: 5DollarFootballAPI Community.
- Competition: Brazil Serie B, provider ID `522514093`.
- Candidate interval: `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`.
- Endpoint: `GET /v1/leagues/522514093/fixtures`.
- Page size: 100.
- Fields: fixture identity, competition, teams, kickoff, status, goals, corners and cards where returned.
- No odds endpoints, no other competitions, no model training, no prediction publication, and no cross-provider automatic joins.

The candidate interval aligns with the observed AI Midas Brazil Serie B snapshot dates. That does not imply 5Dollar has the same coverage or that AI Midas rows are the expected 5Dollar count.

## 2. Evidence supporting the plan

- Community plan account and Brazil competition catalogue verified in Actions run [#43884649616](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43884649616).
- Brazil Serie B competition ID `522514093` confirmed.
- One-request endpoint sample returned HTTP 200 and 8 rows for 2026-11-07 through 2026-11-08 UTC in run [#43916841159](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43916841159).
- The sampled page reported `count=8` and `has_more=false`. Treat `count` as observed page metadata only; do not assume it means a season total.
- Existing adapter and provider qualification record support the league-specific start/end route and pagination parameters. The two-day probe is still the only new-repository fixture-response sample.
- Community quota reported as 300 requests/hour and 20 requests/minute burst. Prior VELTRIX historical qualification used a 40-request ceiling; retain that conservative ceiling for this isolated pilot.

## 3. Hard request budget

**Maximum fixture-endpoint requests for the entire pilot: 40.**

- 34 initial date-window requests are budgeted.
- Up to 6 additional page requests are reserved for windows reporting `has_more=true`.
- Each request uses one competition, one date window, one page, and `per_page=100`.
- No automatic retries. A transient failure is recorded and the run stops for review.
- Throttle to no more than 5 requests/minute, comfortably below the Community burst limit.
- The worker must atomically increment a run-level request counter before each network call and refuse request 41.
- Do not make status, competition-discovery, odds, or other provider calls inside this collection run.

If the required pages exceed the 40-request ceiling, stop with a resumable incomplete run. Do not silently raise the ceiling or widen the plan.

## 4. Date-window strategy

Split the half-open candidate interval into contiguous seven-day windows:

- Window 1 starts 2026-03-21T00:00:00Z.
- Each window ends exactly seven days after its start, exclusive.
- The final window is clipped at 2026-11-09T00:00:00Z.
- No overlaps or gaps are permitted.
- Convert boundaries to UTC Unix seconds exactly as the adapter does.

A seven-day window is a collection-planning choice, not a claim that every seven-day interval is complete after one page. For each window:
1. Request page 1.
2. Validate HTTP status, response envelope, row schema and pagination object.
3. Persist response provenance, checksum, row counts and checkpoint before advancing.
4. If `has_more=false`, mark that window page-complete.
5. If `has_more=true`, request the next page only if the global 40-call budget has capacity.
6. Continue until `has_more=false` or the hard ceiling/stop condition is reached.

The league endpoint's wider date-window support is documented in the provider API review; this pilot still validates every actual response and stops on unexpected behaviour.

## 5. Checkpoint and idempotency requirements

Every run must have:
- immutable run ID and plan version;
- provider, competition ID, date interval and page size;
- hard request ceiling and actual request counter;
- current window start/end and next page;
- last successful request ID, retrieval timestamp, HTTP status and response checksum;
- row count, pagination metadata, duplicate count, invalid count and quarantine count;
- terminal state: COMPLETED, INCOMPLETE_BUDGET, STOPPED_PROVIDER_ERROR, STOPPED_SCHEMA_DRIFT, or STOPPED_RIGHTS.

A page is checkpointed only after its raw response evidence and normalized records are committed in the same database transaction. Replaying a page must be idempotent by provider + provider record ID + observation identity; do not create duplicate fixture identities or overwrite immutable source sightings.

No cross-provider fixture merge is allowed during ingestion. Provider-local IDs remain authoritative until a separately reviewed crosswalk exists.

## 6. Validation and stop conditions

Stop the run immediately on:
- HTTP 401, 403, 301, unexpected redirect, or other non-success status;
- HTTP 429 (record Retry-After, but do not retry in this run);
- invalid JSON or unexpected `success` envelope;
- missing/non-list `data`;
- malformed pagination or non-boolean `has_more`;
- fixture rows missing required IDs, teams, league, or timezone-aware kickoff;
- invalid score/stat values or contradictory settled-score semantics;
- repeated fixture IDs with conflicting immutable identity/score data;
- page count or response behaviour inconsistent with the page request;
- request counter reaching 40;
- database transaction, rights approval or checkpoint failure.

Every rejected record must be retained in a quarantine record with a reason code. Never silently coerce invalid scores or treat unknown statuses as settled.

## 7. Rights and point-in-time controls

- Use the approved 5Dollar Community source scope for Brazil Serie B fixtures/results only.
- Community terms permit internal caching and use in the user's own product; raw response resale/redistribution is prohibited.
- Keep raw response evidence private. Do not commit provider payloads or API credentials.
- If these fields are ever displayed in a public-facing product, include the required attribution: **Football data by 5DollarFootballAPI** with the provider link.
- The API does not expose the original result-publication timestamp. Store the documented four-day post-kickoff availability proxy with `point_in_time_certifiable=false`; never claim it is an exact source publication timestamp.
- Settled scores may be used as target labels subject to rights and integrity checks. Post-match statistics are descriptive-only unless independent point-in-time evidence is obtained.
- No 5Dollar Community odds are included; the historical odds endpoint is not CLV-qualified.

## 8. Database and execution gate

This plan does not provision a database or authorize live collection.

Before execution:
1. Provision a separate private PostgreSQL database for VELTRIX AI ANALYST; never reuse the legacy VELTRIX Football database.
2. Apply the checksum-verified migrations with the explicit expected database name and remote opt-in.
3. Register and verify the effective 5Dollar source approval for this exact competition, data types, use and terms evidence.
4. Test the full ingestion/checkpoint transaction path against ephemeral PostgreSQL.
5. Run a dry-run that enumerates the 34 date windows and proves the request counter refuses request 41.
6. Execute the pilot only after all preceding checks pass.

## 9. Acceptance criteria

The pilot is accepted only if:
- all 34 date windows are accounted for as complete or explicitly incomplete;
- actual API calls do not exceed 40;
- every successful page has a checksum, retrieval time, request metadata and durable checkpoint;
- every fixture has stable provider-local identity and timezone-aware kickoff;
- settled-score semantics are enforced and anomalies quarantined;
- duplicates/conflicts and missingness are quantified;
- no raw provider data or credentials enter the public repository;
- no source-publication timestamp or PIT eligibility is inferred from kickoff time;
- the final report clearly distinguishes observed coverage from unqueried dates.

## 10. Current execution state

- Plan written: yes.
- Provider requests made for this plan: zero.
- Database provisioned: no.
- Historical import: not started.
- Models/predictions changed: no.
