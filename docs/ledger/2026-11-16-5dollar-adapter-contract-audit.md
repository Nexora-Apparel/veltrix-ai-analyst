# 5Dollar adapter contract audit — 2026-11-16

**Scope:** Offline review of the bounded fixture probe evidence against the existing provider adapter. No provider request was made during this audit.

## Verified compatibility

The existing adapter in `backend/app/providers/five_dollar.py` uses the same route family and query contract as the successful probe:

- Route: `/v1/leagues/{competition_id}/fixtures`.
- Query parameters: `start_time`, `end_time`, `status=all`, `page`, `per_page=100`.
- Authentication: Bearer token.
- Response envelope: `success=1`, `data` list, optional `pagination` object with `has_more`.
- Normalizer consumes the sampled fixture keys: `id`, `league`, `teams`, `kickoff_utc` / `kickoff_ts`, `status`, `status_code`, `status_reason`, `goals`, `corners`, and `cards`.

The existing implementation already:
- preserves provider-local fixture/team/competition IDs;
- normalizes timezone-aware kickoff values to UTC;
- supports epoch-second kickoff fallback;
- maps goals, corners and yellow/red card counts;
- prevents unsettled fixtures from carrying final scores;
- paginates until `has_more=false`, with a configurable page ceiling;
- stops on rate limits and reports moved competition IDs without following redirects.

## Test enhancement

Added `backend/tests/test_five_dollar_observed_contract.py` with offline synthetic contract tests. The tests cover:
1. The observed league-fixture route and query parameter names/values for the exact probe interval.
2. An eight-row response with the observed pagination keys and `has_more=false`, asserting only one request is made.
3. Normalization of the sampled field families and finished-score semantics.
4. The `kickoff_ts` fallback when `kickoff_utc` is absent.

The test fixture is synthetic and is not represented as a copy of the provider's raw response. No raw payload was retained.

## Verification

- Test commit: `447edf17383b095ba020ddb016369613b93a2736`.
- CI run: [#43917944552](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43917944552).
- CI status at ledger creation: queued/in progress; no test or lint success is claimed until the run completes.

## Remaining qualification limits

- The probe establishes endpoint reachability and a sampled response schema only for 2026-11-07 through 2026-11-08 UTC.
- It does not establish season-wide pagination completeness or the semantics of every nested statistic.
- `kickoff_utc` / `kickoff_ts` are match kickoff/event-time fields, not source publication or record-availability timestamps.
- No historical import, database write, odds request, or model operation was performed.

## Next steps

1. Confirm CI run #43917944552 passes backend tests, Ruff, and Android build.
2. If CI exposes failures, correct them and rerun before accepting this contract-test addition.
3. Design the resumable historical collection budget only after a separate review of date coverage, page ceilings, and Community quota.
