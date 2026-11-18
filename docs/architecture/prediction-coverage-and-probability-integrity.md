# Prediction coverage and probability integrity

## Product objective

VELTRIX AI ANALYST is a private, personal-use football analysis application. It should produce evidence-based probabilities across the competitions and fixtures available through the configured provider access, without fabricating certainty or needlessly excluding fixtures.

## Probability integrity — mandatory

1. No hardcoded probability vectors, percentages, fallback priors, or fixed market outputs may be used as predictions.
2. Every published probability must be traceable to a versioned model, its input snapshot, feature-availability record, and inference timestamp.
3. Probabilities must be calculated from model outputs. Calibration may transform model scores only through a fitted calibrator trained on chronologically prior, out-of-sample predictions. Calibration must never force outcomes toward a target percentage or fixed distribution.
4. Missing or sparse features must not trigger a generic fixed probability. Use a documented model path that supports the available feature set, with uncertainty and coverage metadata.
5. If no statistically defensible probability can be produced for a market, mark that market unavailable rather than inventing a number. This must not automatically suppress other markets or the fixture itself.
6. Probabilities for mutually exclusive outcomes must be valid, sum to one within numerical tolerance, and be validated before persistence and display.
7. Persist model version, calibration version, feature snapshot/version, input cutoff, and prediction provenance for reproducibility.
8. Do not tune thresholds, calibrators, or model weights on the final evaluation period.

## Broad fixture coverage — avoid unnecessary rejection

- Discover and retain all fixtures returned within the provider's available free-tier access and supported competition scope.
- Do not require an arbitrary minimum number of team matches (such as five) as a universal fixture-admission rule.
- Sparse-history teams may use hierarchical/competition-level estimation with uncertainty that reflects the limited evidence; do not silently substitute a constant global prior.
- Missing optional statistics (for example xG, lineups, PPDA, or detailed shot data) must reduce feature coverage, not automatically reject the fixture.
- Use model variants or feature-aware inference paths that can operate on the evidence actually available.
- Reject or quarantine only for concrete integrity reasons: invalid or contradictory fixture identity, malformed essential fields, impossible chronology, unresolved duplicate identity, unsupported status, or inability to produce a valid market distribution.
- A fixture can remain in the dataset and be displayed as scheduled/research-only even when one or more prediction markets are unavailable.
- Record a reason code for every withheld fixture or market. Monitor rejection rates by competition and reason so one league or data-poor cohort is not silently excluded.

## Duplicate prevention and correction history

- Define one canonical fixture identity using provider fixture identity plus verified canonical competition, season, teams, and kickoff reconciliation.
- Enforce database uniqueness for the canonical fixture and prediction key (fixture, market, model release/inference generation as appropriate).
- Make ingestion and prediction writes idempotent. Reprocessing the same provider response must not create a second fixture, result, or current prediction.
- Separate the current authoritative prediction from immutable prediction history. A genuine model refresh creates a versioned revision, not an indistinguishable duplicate.
- Results are attached once to the canonical fixture; corrections update the authoritative result with an audit trail rather than inserting a second result.
- Preserve conflicting raw provider records for investigation. Do not merge aliases or delete suspected duplicates without traceable identity evidence.
- UI and API responses must return one current prediction per canonical fixture/market while retaining revision history for audit.

## Required tests

- Static and behavioral checks reject fixed probability fallbacks and hardcoded prediction percentages.
- Distinct input fixtures produce probability outputs from the model path, not copied constants.
- Probability distributions are finite, bounded, and normalized.
- Calibration is fitted only on prior out-of-sample data and is versioned.
- Sparse-history and missing-optional-feature fixtures remain eligible for supported inference paths.
- A genuinely invalid fixture is withheld with a reason code; one unavailable market does not suppress unrelated markets.
- Repeated ingestion and inference are idempotent.
- Duplicate provider IDs/aliases and conflicting fixture identities are quarantined without destructive merges.
- Result corrections preserve audit history and never create duplicate result rows.
- Competition-level coverage and rejection metrics are reported for every evaluation run.

## Release policy

These are architecture requirements, not claims that all controls are already implemented. Each requirement must be mapped to code and automated tests before being marked complete. Model performance must be established with chronological out-of-sample and prospective evaluation; no accuracy target is assumed in advance.
