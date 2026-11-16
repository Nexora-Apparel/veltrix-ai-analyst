# Feature eligibility and point-in-time data policy

**Document ID:** VAA-DATA-PIT-001  
**Version:** 1.0  
**Date:** 2026-11-16  
**Status:** Design control; enforce before feature-table construction or model training.

## 1. Purpose

Prevent temporal leakage and unsupported feature claims in VELTRIX AI ANALYST. A statistic is not a valid pre-match feature merely because it describes an event that happened before kickoff. The system must establish when that statistic became available to the model.

This policy is independent of VELTRIX FOOTBALL 2.0. No legacy priors, feature tables, model weights, calibration or prediction logic may be imported.

## 2. Required temporal fields

Every source observation and every derived feature must retain, where applicable:

- `event_time`: when the underlying match/statistical event occurred.
- `source_published_at`: publication timestamp supplied by the source, if trustworthy.
- `first_observed_at`: earliest timestamp this system actually retrieved the value.
- `available_at`: earliest defensible time the value could have been known by the prediction system.
- `retrieved_at`: timestamp of this particular retrieval.
- `point_in_time_certifiable`: explicit boolean; default false unless the evidence supports it.
- source ID, provider record ID, response/checksum linkage, rights approval ID, and transformation version.

Never substitute kickoff time, file commit time, current retrieval time, or a heuristic delay for a source publication timestamp.

## 3. Current source eligibility matrix

| Source/data class | Permitted use now | Pre-kickoff feature eligibility |
|---|---|---|
| 5Dollar fixture identity, teams, competition, kickoff | Fixture catalogue and identity | Not a predictive feature |
| 5Dollar final score/result | Target labels after settlement; historical outcome reporting | Not a pre-match feature |
| 5Dollar corners/cards/goals returned post-match | Descriptive analysis and post-match audit | Not eligible without independently proven pre-kickoff availability |
| 5Dollar four-day post-kickoff availability proxy | Retrieval/availability annotation only | Not PIT-certified |
| AI Midas Brazil Serie B advanced team-match CSV | Descriptive analysis and data-quality comparison | Not PIT-certified; no pre-match use |
| Timestamped pre-match odds from an independently qualified source | Candidate market baseline and CLV research | Eligible only after bookmaker, market, timestamp, and rights validation |
| Lineups, injuries, suspensions, weather, travel/rest | Candidate features | Eligible only when source availability precedes the exact prediction cutoff |

The 5Dollar Community historical odds endpoint is not CLV-qualified and is excluded from this collection plan. AI Midas rows remain non-commercial, descriptive-only candidates until source-specific temporal evidence supports a stronger classification.

## 4. Prediction-cutoff rule

For a prediction with cutoff (T), a feature row is eligible only when:

1. `available_at <= T`;
2. the timestamp semantics and source provenance are recorded;
3. the source approval permits the intended use;
4. the observation is not quarantined, conflicted, or otherwise invalid;
5. the transformation can be reproduced from versioned inputs.

If `available_at` is unknown or only approximated, the feature is excluded from the PIT training set. It may remain in a separate descriptive or post-match table.

## 5. Target-label rules

- Derive 1X2, total-goals and BTTS labels only from a settled fixture with validated final scores.
- Preserve the provider's original status and score fields alongside normalized labels.
- Do not infer settlement solely from non-null goals.
- Quarantine contradictory statuses, scores, identities or duplicate records with conflicting immutable values.
- Label availability is separate from feature availability. A post-match result can be a valid training target without being a valid pre-match feature.

## 6. Dataset partitioning and evaluation

- Split chronologically by kickoff and enforce feature availability at each prediction cutoff.
- Do not randomly split repeated observations of the same fixture across train/validation/test.
- Group by fixture identity for all derived team rows and market snapshots.
- Fit imputers, scalers, encoders, feature selection and calibration only on the training period.
- Keep a temporal gap/embargo where rolling windows or delayed source updates could cross partition boundaries.
- Report coverage and exclusion reasons per source, feature and time period.
- Maintain a frozen prospective evaluation set; no tuning against its outcomes.
- Any walk-forward result must be reproducible from immutable dataset manifests and code/model versions.

## 7. Feature registry contract

Before a feature enters model training, register:

- stable feature name and definition;
- entity/grain (team-match, fixture, team-at-cutoff, market snapshot);
- source(s) and source approval IDs;
- event-time and availability-time semantics;
- prediction cutoff rule;
- missingness and conflict handling;
- transformation code/version;
- PIT eligibility status and evidence;
- permitted use and retention constraints.

Unknown temporal semantics default to `DESCRIPTIVE_ONLY`, not eligible.

## 8. Acceptance gate

No model training begins until:
- the historical import quality validator passes;
- target-label completeness and settlement semantics are measured;
- a source-by-source PIT eligibility matrix is populated from observed evidence;
- the feature registry is reviewed;
- chronological splits and leakage tests pass;
- excluded post-match fields are demonstrably absent from pre-match feature views.

This policy does not certify the current datasets or any model. It defines the controls required for a future certification.
