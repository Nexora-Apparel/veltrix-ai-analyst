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

## Match evidence labels — app presentation

The match list must use only these three short evidence labels:

- **STRONG** — broad, sufficiently complete and reliable fixture-specific evidence is available.
- **MEDIUM** — useful evidence exists, but some important history or supporting features are missing or incomplete.
- **LOW** — very limited or no fixture-specific evidence is available; use the best validated fallback path where possible and reflect the resulting uncertainty.

The label is an evidence-coverage indicator, not a prediction-confidence rating, probability, expected result, or guarantee. A STRONG match can still be difficult to predict; a LOW match can still have a valid model estimate.

### Classification contract

- Calculate the tier from a versioned evidence-quality assessment, not from a single team-match-count cutoff.
- The assessment should account for source reliability and freshness, team-history coverage, competition context, and availability of relevant supporting features. Missing optional features reduce the assessment; they do not automatically reject the fixture.
- Use measured feature coverage and evidence quality. Do not invent missing values or award coverage for unavailable data.
- Define and version the tier boundaries using development/validation data, then freeze them for each evaluation or release. Do not tune boundaries against the final test period or to make the app display a preferred distribution of labels.
- The same evidence snapshot and assessment version must produce the same label. Persist the tier, assessment version, and underlying coverage metadata for audit.
- If a fixture has no usable fixture-specific evidence, label it LOW. Still retain and process it through a validated competition-level fallback when possible. If a particular market cannot be estimated defensibly, show that market as unavailable rather than inventing a probability or hiding the whole fixture.
- The match card should display the label only. Do not put technical notes, missing-feature lists, evidence percentages, or long explanations on the main match card. Detailed evidence metadata may remain available in internal diagnostics/audit views.

### Sparse-history modelling and fallback hierarchy

- Use the normal statistical calculation path with the evidence actually available. For goal-based markets, this includes Dixon–Coles/Poisson score modelling where its required inputs can be estimated.
- Estimate team attack/defence strength from available team history. When team-specific samples are sparse, use learned hierarchical shrinkage toward competition-level and, where justified, broader population estimates. The amount of shrinkage must be learned/validated from data and reflect sample size; it must not be a hardcoded probability.
- With one or a few prior matches, use those observations as evidence while accounting for their high variance. Do not treat a small sample as conclusive, and do not discard it merely because it is below an arbitrary count.
- If one team has history and the other has little or none, retain the available team's evidence and estimate the other through the hierarchical model. Do not force a home win, draw, away win, or generic fixed distribution.
- If team-specific history is absent, use the best validated competition-level model path available, with appropriately wider uncertainty and a LOW evidence marker. If even that path cannot support a defensible estimate, retain the fixture but mark the affected market unavailable.
- Model fallback means switching to a validated calculation path using available evidence, not copying a canned probability vector or inventing missing statistics.
- Do not fabricate xG, lineups, injuries, or team history. Missing features remain missing and are represented in the feature-coverage record.

## Broad fixture coverage and evidence-tiered prioritisation

### Coverage policy

- Discover and retain all fixtures returned within the provider's available free-tier access and supported competition scope.
- Do not require an arbitrary minimum number of team matches (such as five) as a universal fixture-admission or prediction rule.
- Never skip a fixture solely because a team has fewer than five previous matches, sparse statistics, or incomplete secondary data.
- The system should prioritise fixtures with stronger, more complete evidence for the primary prediction workload, because those fixtures support more reliable estimates.
- After the stronger-evidence fixtures are processed, it must also process lower-evidence fixtures through supported fallback model paths. Low evidence is a reason to widen uncertainty and disclose limitations, not a reason to silently drop the match.
- Evidence prioritisation must not become a favourites-only, popular-leagues-only, or high-data-only filter. Track coverage across competitions and evidence tiers.
- Missing optional statistics (for example xG, lineups, PPDA, or detailed shot data) must reduce feature coverage, not automatically reject the fixture.
- A fixture can remain in the dataset and be displayed as scheduled/research-only even when one or more prediction markets are unavailable.

## Admission and withholding

- Use model variants or feature-aware inference paths that can operate on the evidence actually available.
- Reject or quarantine only for concrete integrity reasons: invalid or contradictory fixture identity, malformed essential fields, impossible chronology, unresolved duplicate identity, unsupported status, or inability to produce a valid market distribution.
- Record a reason code for every withheld fixture or market. Distinguish data-integrity rejection from a market-specific inability to estimate.
- Monitor rejection and prediction rates by competition, team-history depth, and evidence tier so data-poor cohorts are not silently excluded.

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
- Evidence tiers are deterministic for the same evidence snapshot and assessment version; tier boundaries are versioned and frozen for final evaluation.
- Tier labels reflect measured source quality, freshness, history and feature coverage, not a fixed minimum team-match count.
- Fixtures with zero, one, two, four, and five-plus prior team matches remain eligible for the appropriate validated model path; no arbitrary five-match cutoff.
- Sparse-history fixtures use learned hierarchical estimates and show wider uncertainty where supported by evaluation.
- One-sided history (one team with history, the other without) uses available evidence without a forced generic probability.
- Stronger-evidence fixtures are prioritised, but lower-evidence fixtures are still processed through fallback paths and counted in coverage.
- Missing optional features do not automatically suppress a fixture or unrelated markets.
- A genuinely invalid fixture is withheld with a reason code; one unavailable market does not suppress unrelated markets.
- Repeated ingestion and inference are idempotent.
- Duplicate provider IDs/aliases and conflicting fixture identities are quarantined without destructive merges.
- Result corrections preserve audit history and never create duplicate result rows.
- Competition-level coverage, evidence-tier distribution, and rejection reasons are reported for every evaluation run.

## Release policy

These are architecture requirements, not claims that all controls are already implemented. Each requirement must be mapped to code and automated tests before being marked complete. Model performance must be established with chronological out-of-sample and prospective evaluation; no accuracy target is assumed in advance.
