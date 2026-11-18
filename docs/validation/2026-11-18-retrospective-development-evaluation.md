# Retrospective development evaluation — 2026-11-18

## Status

**DEVELOPMENT ONLY — NOT PIT-CERTIFIED — NOT A PRODUCTION RELEASE**

This report records a chronological retrospective research run over the existing approved 5DollarFootballAPI source records. It does not certify prospective performance, cross-competition generalization, evidence-tier calibration, or commercial use.

## Source dataset

- Provider: `5DollarFootballAPI`
- Source ID: `5dollarfootballapi`
- Finished fixtures: 380
- Distinct provider team IDs: 20
- Independently represented competitions: 1 (Brazil Serie B, provider competition ID `522514093`)
- Date span: 2026-03-21 through 2026-11-14
- Unique provider fixture IDs: 380 / 380
- Dataset MD5 over ordered fixture identity, kickoff, competition, provider team IDs and final scores: `592f17205e1007b5b18b5a63464812c4`

The retrospective development run used provider team IDs as opaque within-provider model keys. It did not approve or alter any canonical identity mappings. The canonical fixture/team/competition identity review records remain unresolved, including one conflicting finished fixture. The dataset is not a prospective point-in-time (PIT) sample: historical source observations were retrieved after their match kickoffs.

## Chronological development protocol

Three expanding-window folds were used. Each model was fitted only on results at or before the fold cutoff, then scored on later fixtures.

| Fold | Training fixtures | Validation fixtures |
|---|---:|---:|
| 1 | 60 | 90 |
| 2 | 150 | 99 |
| 3 | 250 | 130 |
| **Total out-of-fold** | — | **319** |

The hyperparameter search evaluated 36 candidates:
- Half-life: 90, 180, 365 days
- Team ridge: 0.1, 0.5, 2, 8
- Competition ridge: 0.5, 2, 8

Selected development candidate: half-life 90 days, team ridge 0.1, competition ridge 2.0. Mean held-out Poisson negative log likelihood: **2.0421647948 per team-goal observation**.

**Interpretation limit:** the dataset contains one competition, so the competition-effect/ridge dimension is not independently identified. The selected competition-ridge value is not a generalization result and must be retuned on multiple competitions.

## Dixon–Coles development rho freeze

- Frozen development rho: **0.1040212798**
- Protocol: pooled profile likelihood on 319 strictly out-of-fold hierarchical goal-rate forecasts
- Development negative log likelihood: 1302.0403467
- Common feasible interval across the OOF rate pairs: [-0.3907711324, 0.3666554544]

This value is frozen for reproducible development comparisons only. It is **not** approved as a production rho. It must be re-estimated if the training population, model family, goal-rate process or development protocol changes, and must be prospectively monitored before any production release.

## Paired model forecasts

Hierarchical Poisson, the repository's existing attack/defence Poisson model, and Elo were scored on the same **319 OOF fixtures** using expected home match score (home win = 1, draw = 0.5, away win = 0).

| Model | Fixtures | Expected-home-score MSE | MAE |
|---|---:|---:|---:|
| Hierarchical Poisson + development rho | 319 | 0.168144 | 0.364370 |
| Existing attack/defence Poisson | 319 | 0.168344 | 0.364301 |
| Elo expected home score | 319 | 0.172347 | 0.372890 |

This is a paired scalar expected-score comparison, not a full 1X2 probability comparison: the existing Elo implementation exposes expected home score but does not expose a draw probability or a complete 1X2 distribution. The existing Poisson diagnostic used its independent-Poisson scoreline setting, while the hierarchical model used the frozen development rho. Therefore these numbers are diagnostic only and are not sufficient to promote one model over another. A proper market-level comparison must add an explicit Elo draw model and use a consistent development protocol.

## Evidence-tier calibration gate

Evidence-tier calibration was **not run** because the current data cannot support defensible historical STRONG / MEDIUM / LOW labels:

- `pre_match_feature_observations`: 0
- `SYSTEM_OBSERVED_AT` source sightings: 0
- All historical source sightings: 1,062
- Canonical provider-team identity links: 21, all `REVIEW_REQUIRED`
- Canonical competition identity links: 1, `REVIEW_REQUIRED`
- Canonical fixture source links: 384, all `REVIEW_REQUIRED`

Historical retrieval timestamps cannot be substituted for information availability at the original kickoff. No historical lineups, xG, PPDA or other pre-match feature values are to be fabricated. Consequently, STRONG and MEDIUM calibration sample sizes are zero; LOW cannot be assigned reliably from the available historical feature evidence either. The tier calibration evaluator remains a diagnostic utility awaiting properly observed evidence signals and sufficient held-out observations per tier.

## Multi-competition generalization gate

The current database contains only Brazil Serie B. No second independently represented competition was available in the stored provider catalogue during this run. Cross-competition generalization is therefore **not evaluated**.

The existing historical importer is hard-scoped to competition ID `522514093`; extending it safely requires a competition-scoped import run, independent request reservations/budgets, raw response retention, source provenance, and identity-review handling for each additional competition. Do not bypass those controls or merge provider aliases automatically.

## Promotion decision

**NO PROMOTION. NO PRODUCTION ORCHESTRATION ACTIVATION.**

The development run establishes that the optimizer converged on the selected chronological folds and yields a reproducible research rho, but it does not meet the user's multi-competition, evidence-tier, prospective PIT, identity-resolution or full-market paired validation requirements. The orchestration service remains gated and is not wired to production routes or persistent audit storage.
