# 2026-11-18 — Bookmaker odds isolation and value-betting capture contract correction

## Change record

- Pull request: [#55 — Enforce bookmaker odds isolation from core predictions](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/55)
- CI run: [#44236392864](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44236392864)
- Merge commit: `8acdb7083180c87420d6e1371b8fad5e985aa5c6`
- Branch: `fix/odds-value-betting-isolation`
- Status: merged to `main`; backend tests, Ruff lint, and Android debug build all passed.

## Implemented safeguards

1. `OddsObservation` no longer carries a model-training permission flag. It now requires the explicit `VALUE_BETTING_ONLY` use purpose and a separate value-betting rights gate.
2. Odds capture preserves independent `request_started_at`, `retrieved_at`, optional `provider_response_date`, `source_tick_at`, `kickoff_at`, and `prediction_cutoff_at` clocks.
3. Capture validation rejects request/retrieval order violations, late retrieval, post-cutoff source ticks, kickoff/cutoff violations, in-play odds, and denied value-betting rights.
4. Prediction evidence has a data-domain classification. Core feature admission rejects `BOOKMAKER_ODDS` and rejects unclassified domains. Football-match data remains the default domain for backwards-compatible existing evidence contracts.
5. Regression tests prove bookmaker odds cannot enter the core prediction feature admission path and unknown domains fail closed.

## CI evidence

Workflow run `44236392864` completed with conclusion `success`:
- Backend tests: passed.
- Ruff lint: passed.
- Android debug build: passed.
- APK upload: passed.

## Scope and non-claims

- No provider API request or quota credit was consumed by this change.
- No Neon/database write, odds ingestion, recurring schedule, production prediction endpoint, model promotion, or Android/backend prediction integration was introduced.
- The boolean rights gate is an explicit contract boundary, not a new provider-rights grant. Provider-specific bookmaker-odds approvals must be reviewed and recorded in the source-rights registry before real observations can be admitted.
- This change does not certify either provider's PIT coverage, value-betting performance, CLV, or market ROI.
- Core football predictions remain independent of bookmaker odds. Missing/invalid odds must not suppress an otherwise eligible football prediction; they only prevent downstream value-bet evaluation.
- Value betting remains locked pending its independent certification requirements.

## Next engineering unit

Review provider-specific rights for bookmaker odds as a distinct data type and value-betting use. Only after the exact provider, sport/competition scope, data type, permitted purpose, attribution and retention conditions are approved should the system add a registry-backed rights decision adapter. Then add a dry-run, one-fixture capture envelope with idempotency tests; do not add a writer or schedule before those gates pass.
