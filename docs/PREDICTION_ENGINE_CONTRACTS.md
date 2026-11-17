# Prediction engine contracts and point-in-time admission

**Document ID:** VAA-ML-CONTRACTS-001  
**Version:** 1.0  
**Date:** 2026-11-17  
**Status:** Stage 3 contract baseline; implementation must conform

## 1. Contract invariants

1. All timestamps are timezone-aware UTC instants at serialization boundaries.
2. Every feature value has immutable source lineage and a transformation version.
3. A feature is eligible only when source publication and defensible availability are at or before the exact prediction cutoff.
4. Rights must be effective at the cutoff and explicitly permit both feature engineering and model training.
5. Fixture and team identities must be verified, not merely suggested.
6. Event time, publication time, first-observed time, availability time and retrieval time are distinct fields.
7. Missing evidence is an exclusion, not a value to impute.
8. A target label may be post-match; a pre-match feature may not.
9. Synthetic test data is never mixed into real dataset manifests or performance metrics.

## 2. Eligible source observation contract

Required fields:

| Field | Type | Rule |
|---|---|---|
| `source_id` | string | Stable qualified source identifier |
| `provider` | string | Provider namespace |
| `provider_record_id` | string | Provider-local identity; never replaced by canonical ID |
| `source_observation_id` | string/integer | Immutable normalized observation ID |
| `sighting_id` | string/integer | Exact retrieval sighting ID |
| `provider_response_id` | string/integer | Captured successful response reference |
| `payload_sha256` | 64-char lowercase hex | Hash of exact observed payload |
| `event_time` | datetime | Underlying event/effective time; may be null only for non-event metadata |
| `source_published_at` | datetime | Verified source publication timestamp; required for PIT |
| `available_at` | datetime | Earliest defensible system availability; required for PIT |
| `retrieved_at` | datetime | Time of this retrieval |
| `availability_basis` | enum | PIT currently requires `SOURCE_PUBLISHED_AT` |
| `point_in_time_certifiable` | boolean | Must be true for PIT use |
| `rights_approval_id` | string/integer | Exact approval record |
| `rights_status_at_cutoff` | enum | Must be active |
| `permitted_uses` | set | Must contain FEATURE_ENGINEERING and MODEL_TRAINING |
| `canonical_identity_status` | enum | Must be VERIFIED |
| `quarantined` | boolean | Must be false |

Additional source-specific semantics and evidence URI/hash must be retained. A provider's general terms do not by themselves certify an individual observation's timestamp.

## 3. Derived feature contract

Each feature value must carry:

- `feature_name`, `feature_schema_version`, `entity_grain`;
- `fixture_id` and/or canonical team ID;
- `value` and explicit unit/semantic definition;
- `prediction_cutoff_at`;
- `source_observation_id`, `sighting_id`, `provider_response_id`, `payload_sha256`;
- `source_published_at`, `available_at`, `retrieved_at`;
- `rights_approval_id`, permitted use evidence and identity status;
- `transformation_id`, code version and input lineage;
- `eligibility_status` and stable exclusion reason code.

Feature snapshots are immutable. A corrected source observation creates a new snapshot/version; it does not rewrite a prior forecast's feature state.

## 4. Fixture prediction request

Required fields:

- `request_id`;
- `canonical_fixture_id`;
- `canonical_competition_id`;
- `home_team_id`, `away_team_id`;
- `kickoff_at`;
- `prediction_cutoff_at` (strictly before kickoff);
- `feature_snapshot_id` and hash;
- `feature_schema_version`;
- `requested_markets`;
- `data_quality_tier`.

Reject when canonical identity is not VERIFIED, the fixture is quarantined/conflicted, kickoff is absent, cutoff is not before kickoff, or feature snapshot does not match the fixture/cutoff.

## 5. Model output contract

Every model result must contain:

- `prediction_id`, `request_id`, `model_id`, `model_version`;
- `algorithm`, `config_hash`, `code_commit`;
- `training_dataset_manifest_id`, `training_cutoff_at`;
- `feature_snapshot_id`, `feature_schema_version`;
- `generated_at`, `prediction_cutoff_at`;
- `market_probabilities` (finite, bounded [0,1], coherent and sum-to-one where mutually exclusive);
- `expected_home_goals`, `expected_away_goals` and scoreline distribution when goal models are used;
- `uncertainty`, `constituent_disagreement`, `coverage`;
- `eligibility_status`, `publication_status`, `abstention_reason_codes`.

A prediction is not publishable merely because probabilities are mathematically valid. Model, data, identity and market-specific approval gates must also pass.

## 6. Point-in-time admission algorithm

For each feature observation at cutoff T, reject unless all conditions hold:

1. The source observation, sighting and captured response exist and are linked.
2. The exact payload hash matches immutable observation evidence.
3. Publication and availability timestamps are present and timezone-aware.
4. Availability basis is an approved, evidenced source-publication basis.
5. `source_published_at <= retrieved_at`.
6. `available_at >= source_published_at`.
7. `source_published_at <= T` and `available_at <= T`.
8. Rights approval is active at T and permits FEATURE_ENGINEERING and MODEL_TRAINING.
9. Canonical identity is VERIFIED; row is not conflicted, quarantined or a duplicate candidate.
10. Transformation lineage and feature schema are versioned.

No rule may substitute kickoff time, event time, retrieval time, provider update time, file commit time or an estimated delay for publication/availability evidence.

## 7. Current dataset disposition

The current 384-fixture Brazil Serie B canonical dataset is not admitted to pre-match feature engineering or model training. Its source observations do not establish publication/availability timestamps; canonical rows remain SOURCE_ROW_ONLY, IDENTITY_REVIEW_REQUIRED or CONFLICT. Settled results may be considered as target labels only after identity, settlement and rights checks. Four UNKNOWN records and two America MG conflict records remain excluded from certified samples.

## 8. Chronological validation contract

Each walk-forward fold records:

- fold ID and deterministic split configuration;
- training, validation and test kickoff boundaries;
- embargo duration and rationale;
- fixture IDs per partition;
- feature snapshot IDs and source-lineage hashes;
- model/config/code versions and training cutoff;
- metrics and sample counts by market and competition;
- exclusions, abstentions and missingness;
- benchmark versions and calibration fit window.

Rules:

- train precedes validation, which precedes test;
- no fixture crosses partitions;
- no feature available after its fixture cutoff is admitted;
- no fitted transform/calibrator/ensemble weight sees test outcomes;
- folds advance forward in time;
- final test periods remain sealed from model selection;
- results are reproducible from the recorded manifest.

Minimum metrics: multiclass Brier and log loss for 1X2; binary Brier/log loss for BTTS and each totals line; joint scoreline log likelihood for goal distributions; calibration/reliability and coverage/abstention. Always report denominators. Do not publish performance metrics for synthetic-only runs as model accuracy.

## 9. Contract versioning

Breaking changes increment the major contract version. Additive optional fields increment the minor version. Every persisted feature snapshot and prediction references the exact contract/schema version used.
