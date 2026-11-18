# Prospective Odds Capture Contract — Design Gate

**Status:** DESIGN ONLY — no collector, database writer, recurring schedule, or model feature activation is authorized by this document.  
**Date:** 2026-11-18  
**Provider:** 5DollarFootballAPI Community  
**Evidence:** bounded snapshot probe run [#44216129899](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44216129899)

## 1. Verified provider behavior

A single request to `GET /v1/fixtures/1194891794/odds` returned HTTP 200 and one Bet365 bookmaker row. The response exposed 12 market keys, including 1X2, BTTS, goal lines, Asian handicap, cards, and corners. Bet365 1X2 opening prices were home 4.10, draw 3.25, away 1.90, with `opened_at=2026-11-09T13:15:09+00:00`.

The probe request began at `2026-11-18T01:29:05.395447+00:00` and the response was retrieved at `2026-11-18T01:29:05.859374+00:00`. The provider's HTTP Date header was `Wed, 18 Nov 2026 01:29:05 GMT`. The response hash was `93c40815c5c587e253cafd2ecbdb55521787ecb9bf1c43611f4fff52b5cf0180`.

This proves endpoint access and field presence. It does not prove that the opening price was available to this system at `opened_at`, nor does it make this late-retrieved historical snapshot eligible for a prior prediction cutoff.

## 2. Clock semantics — never conflate

Every captured observation must preserve distinct clocks:

- `request_started_at`: local UTC timestamp immediately before the HTTP request.
- `retrieved_at`: local UTC timestamp immediately after the response body is fully received.
- `provider_response_date`: optional HTTP Date header; transport/server metadata only.
- `source_tick_at`: provider `opened_at` or history `recorded_at`, retained as provider-reported event time only.
- `fixture_kickoff_at`: fixture event time from the verified fixture record.
- `prediction_cutoff_at`: immutable cutoff used by the forecast being evaluated.

Do not rename `source_tick_at` to `available_at`. Do not infer availability from `opened_at`, `recorded_at`, HTTP Date, kickoff, or a later database insertion timestamp.

## 3. PIT admission rule

An odds observation may enter a prospective prediction's PIT feature set only when all conditions hold:

1. The exact response was received by this system before the prediction cutoff: `retrieved_at <= prediction_cutoff_at`.
2. Request and retrieval timestamps are timezone-aware UTC instants and ordered correctly.
3. Fixture ID matches the requested fixture and the fixture's verified kickoff is later than the cutoff.
4. Provider response is successful and schema-valid; bookmaker, market, selection, line and decimal price are explicit.
5. The market/selection mapping is allowlisted and tested. Unknown market names are retained only in the raw schema manifest, never silently mapped.
6. The source approval record explicitly permits the intended internal feature-engineering/model-training use and is active for the exact provider, data type and scope.
7. The response hash, request identity and capture-run identity are persisted, immutable and reproducible.
8. No in-play/suspended state is present; ambiguous state fails closed.
9. Duplicate delivery is idempotent by a stable observation identity, without overwriting prior evidence.

A historical source timestamp earlier than cutoff does not satisfy condition 1 if retrieval occurred after cutoff. The 2026-11-18 probe observation for fixture 1194891794 is therefore **not PIT-admissible** for a cutoff before retrieval.

## 4. Capture envelope

The future capture runner should emit a minimal, privacy-safe manifest and persist structured observations only after validation. Required envelope fields:

- capture_run_id, request_id, provider, endpoint, fixture_id
- request_started_at, retrieved_at, provider_response_date
- HTTP status, response byte count, response SHA-256
- schema version, bookmaker slug/name, market key
- selection, optional line, decimal price, source_tick_at
- fixture_kickoff_at, prediction_cutoff_at
- source approval ID/version and permitted-use decision
- admission result and explicit rejection reason

Never log API keys, authorization headers, full raw responses, or unredacted request headers. Retain only data allowed by the source approval and provider terms.

## 5. Initial operating envelope

- Keep collection manual-only during validation.
- One fixture per dispatch initially; hard maximum one HTTP request per fixture.
- No retries, no pagination, no history endpoint calls, no bulk odds endpoints, and no concurrent fan-out.
- Reuse the existing Community credential; do not create another account/key.
- Track rate-limit headers and enforce a conservative local budget below the 300/hour provider limit and 20/minute burst.
- Do not schedule recurring capture until the schema, PIT admission, rights, idempotency and quota tests pass.
- Do not call the Ultra-only full odds history endpoint with the Community plan.

## 6. Implementation sequence

1. Add pure typed capture contracts and a fail-closed manifest schema.
2. Add parser tests using sanitized fixtures based on the verified live envelope; cover all observed market keys without assuming every market has a source timestamp.
3. Add PIT boundary tests: retrieved one microsecond before cutoff accepted; equal cutoff accepted only if policy explicitly retains inclusive semantics; retrieved after cutoff rejected; source timestamp before cutoff with retrieval after cutoff rejected.
4. Add malformed envelope, fixture mismatch, timezone-naive timestamp, partial price, suspended/in-play, unknown market, rights denial and duplicate/idempotency tests.
5. Add a dry-run-only manual workflow that validates and emits a manifest without DB writes.
6. Review test evidence and provider terms; only then propose a separate guarded database-writer change.
7. Begin prospective capture with a small manually selected fixture set; evaluate coverage and timestamp quality before using odds in any model or CLV benchmark.

## 7. Explicit non-goals and release gates

This design does not authorize:
- retrospective backfill of availability timestamps;
- full historical odds reconstruction;
- production odds ingestion or automated recurring collection;
- odds-derived model training before PIT and rights gates pass;
- value-bet selection, CLV claims, betting recommendations or public publication;
- production prediction endpoints, model promotion or Android prediction integration.

The existing retrospective model comparison is unchanged: fixed v1 remains the research benchmark candidate, v2 remains an immutable comparator, and neither is PIT- or production-certified.
