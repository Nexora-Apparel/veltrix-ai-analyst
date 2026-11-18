# Prospective point-in-time evidence contract

## Purpose

The six-competition 2026-11-18 corpus is retrospective: all 614 observations were first retrieved after kickoff and none is PIT-certified. This contract applies only to new observations captured prospectively. It must never relabel historical rows.

## Capture transaction

1. Resolve the fixture from the provider using the exact provider, source, competition ID and fixture ID. Preserve provider-local team IDs and kickoff timestamp as returned; store any independently verified kickoff correction as a separate adjudication, never overwrite raw source evidence.
2. Fetch the source response once. Persist the exact response bytes in the immutable provider-response record, including its response ID, HTTP status and retrieval timestamp. Calculate SHA-256 over those exact bytes, not parsed/re-serialized JSON.
3. Insert the observation in the same transaction with `system_observed_at DEFAULT clock_timestamp()`; retrieve the database-generated value with `RETURNING`. Never accept an application-supplied value for this field.
4. Store source publication/availability timestamps only when explicitly supplied by the provider and retain their provenance. A retrieval timestamp is not a publication or availability timestamp.
5. Store the fixture identity tuple: provider, source ID, provider competition ID, provider fixture ID, home/away provider team IDs and timezone-aware kickoff.
6. Mark the observation PIT-certifiable only when `system_observed_at < kickoff_at`. Equality is not pre-match. Post-kickoff observations remain auditable but cannot be used as pre-match features.
7. Keep every observation immutable. Corrections and later responses create new observation rows; never update the prior raw payload/hash/response ID.

## Training dataset construction

- Build expanding-window datasets by fixture kickoff time, not retrieval time.
- A training label is usable only after the fixture is finished and its final score is present.
- A feature snapshot is usable for a target only if its own DB `system_observed_at` is strictly before that target kickoff.
- Group simultaneous kickoffs atomically; no fixture from a simultaneous group may enter another fixture's history.
- Fit preprocessing, calibration, hyperparameter selection and feature selection within each training fold only.
- Retain provider-local IDs. No inferred team aliases or fixture merges.
- Keep retrospective outcome-only research separate from prospective PIT feature evaluation.

## Evaluation extensions

Report independently for 1X2, BTTS and O/U 2.5:
- fixture count and market label coverage;
- Brier score and log loss;
- calibration intercept/slope and reliability bins;
- per-competition sample count and metrics;
- paired bootstrap confidence intervals for model-minus-baseline score deltas, resampling fixtures within competition and preserving paired predictions;
- fold boundaries, dataset fingerprint, source-observation IDs, response IDs and hashes.

Do not pool markets with different label coverage. Missing market labels are excluded only from that market's denominator and counted explicitly. Bootstrap intervals are descriptive unless the pre-registered test protocol and sample-size requirements are met.

## Release locks

No release artifact is eligible until every market's walk-forward evaluation has at least 1,000 matches, prospective settled selections at least 300, at least 90 distinct dates, timestamped odds coverage at least 98%, net ROI above zero with lower 95% ROI bound above zero, and 1X2 improves on bookmaker Brier and log loss. These are certification thresholds, not targets to optimize against. Until all checks are independently reproducible and signed into an immutable release artifact, production promotion and value betting remain locked.
