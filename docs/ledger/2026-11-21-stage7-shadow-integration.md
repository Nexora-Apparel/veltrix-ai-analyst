# 2026-11-21 — Stage 7 research-only Newton shadow integration

## Base and source-of-truth reconciliation

- Integration branch base: `main` at `da86cef52d51a7b8924ad837fe91208a30f562c5`.
- Direct commit comparison confirms `82d0f42f0cfda19442887495ef6132d22a9a187b` is an ancestor of `da86cef`; main is identical to `da86cef`.
- PR #143 supplied the Newton solver/evaluator and v3.2 workflow; PR #144 corrected the canonical config fingerprint. PRs #139–#141 are unrelated and untouched.
- Stage 7 run: `44929166889`; artifact: `14717051631`; evaluation commit: `da86cef52d51a7b8924ad837fe91208a30f562c5`.
- Aggregate JSON SHA-256 (computed from downloaded artifact member `shrinkage-retrospective-evaluation.json`): `c724bb52677f3b93040028824ecc547f756e69c01586c7e9f9a587f75132f83d`.
- Aggregate ZIP SHA-256: `0cef6a553ceab068a38bd24a3b515fc16cc95bdfda3963f960927d8c53a96718`.

## Selected model freeze and admission

- Model version: `hierarchical-poisson-newton-shadow-v2`.
- Selected values: k=4, half-life=730 days, blend=1.0, damped Newton with analytic Hessian/backtracking.
- New frozen config: `docs/research/hierarchical-poisson-shadow-v2.json`.
- Canonical config SHA-256: `87063b2ddec253c65ce4071ce9e508d396c2ee5bb11b8dd85513dc97260d0698`.
- Committed admission record: `backend/app/research/admissions/hierarchical-poisson-newton-shadow-v2.json`, tier `SHADOW`, certification `RETROSPECTIVE_NOT_PIT_CERTIFIED`.
- Admission binds config SHA `87063b2ddec253c65ce4071ce9e508d396c2ee5bb11b8dd85513dc97260d0698`, training SHA `d70ee34940c8fc6681f3cd5751d4fdcc2e876b307fe388d9f3a792c73e34b262`, and report SHA `c724bb52677f3b93040028824ecc547f756e69c01586c7e9f9a587f75132f83d`.
- Existing fitting defaults and old forecast path are not changed. The new runner explicitly selects Newton and the frozen values.

## Abstention diagnostic

- Rule fixed before any live output: abstain with `ABSTAIN_INSUFFICIENT_TEAM_HISTORY` when either side has fewer than five training matches.
- Recomputed against the pinned Stage 6 dataset and the exact Stage 7 fold date/cutoff construction: 220 of 490 development-fold test fixtures (44.897959%) would have been affected; fold details are in `docs/research/stage7-abstention-diagnostic.json`.
- This is diagnostic only; Stage 7 retrospective scores were not retroactively changed.

## Per-run concentration monitor

For slates of at least 15 forecasts, quarantine if any condition is met:
- P(home) population SD below 0.08 or above 0.22.
- Any single 1X2 outcome is top pick in more than 85% of fixtures.
- BTTS-yes pick share exceeds 90%.
- Over-2.5 pick share exceeds 90%.

Also report, without gating, the share with P(draw)>0.50 and the share with any forecast probability>0.80. Smaller slates are not concentration-gated. A quarantined run writes a non-ready status and no forecast rows to the research response.

## Feed and workflow controls

- Research API requires both the committed model-version-matched SHADOW admission record and `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED=true`. The display flag defaults off; this PR does not expose forecasts in the app.
- Research responses are labelled `RESEARCH ONLY` and `RETROSPECTIVE_NOT_PIT_CERTIFIED`; publication remains NOT_PUBLISHED and value betting remains LOCKED.
- Existing `prospective-shadow-predictions.yml` schedule/workflow-run path remains hard-disabled (`if: false`).
- Added `.github/workflows/research-shadow-inference.yml` with `workflow_dispatch` only and an explicit boolean confirmation before isolated research-ledger persistence. No schedule, automatic workflow_run trigger, production prediction writes, odds calls, or provider calls.

## Known limitations and non-blocking follow-up

- Archived-model paired date-block intervals are not in the Stage 7 aggregate artifact; the supervisor's approximate mean gain (~0.04) is not represented as an interval or treated as independently verified here.
- Training-fixture P(home) dispersion has not been recomputed in this integration.
- The seven fold-4 competition UUIDs are not mapped to display names in the aggregate artifact; no names are guessed.
- The 28 unresolved identity cases remain unverified.
- These are documentation/research follow-ups, not release promotion criteria. No accuracy claim is made.

## Owner gates — not executed by this PR

1. Review and merge this draft PR after exact-head CI is green.
2. On GitHub Actions, open **VELTRIX Stage 7 research shadow inference (manual only)**, choose **Run workflow**, keep branch `main`, set `confirm_research_ledger_write=true`, and confirm. This is the first action that writes a research run to Neon.
3. Before app visibility, inspect the uploaded sanitized run summary and five sample forecasts. Only then may the owner separately set `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED=true` in the deployment environment.
4. Do not enable schedules, change production/value locks, or publish production forecasts under this admission.

