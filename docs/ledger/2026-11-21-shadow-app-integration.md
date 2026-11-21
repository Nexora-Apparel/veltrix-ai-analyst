# 2026-11-21 — Research forecast app integration

## Objective
Expose the 21 November 2026 prospective shadow forecast batch in the existing Android Predictions, BTTS and Over/Under screens without promoting it into production publication.

## Verified source artifact
- Shadow workflow run: [44873166128](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44873166128)
- Artifact: [veltrix-prospective-shadow-forecasts](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44873166128/artifacts/14694089682)
- Artifact SHA-256: `44164d6e9ead148b6fa0e663f81bde18ad5f75e839143e408a2ecce98cc7f16f`
- Status: `SHADOW_FORECASTS_READY`; 25 forecasts, 25 fresh upcoming snapshots, 0 abstentions.
- Model: `hierarchical-poisson-shadow-v1` / `HIERARCHICAL_POISSON_DIXON_COLES`; optimizer converged in 57 iterations. Dixon–Coles rho remained zero because inner OOF evidence was insufficient.
- Training-only history: 996 cutoff-valid historical labels, 136 teams, seven competitions. These are not prospective settled selections.
- Dataset SHA-256: `80148b3f0f42e70d94391d9283c42f35b5b92e1631a9a1cb7baee899373dad0c`.
- The report uses historical goal outcomes only; captured auxiliary features are audited but not used in probabilities pending prospective validation.
- No bookmaker odds; provider calls 0; DB writes 0 in the original inference job.
- All forecasts are `NOT_PUBLISHED`; release eligibility false; production promotion and value betting remain `LOCKED`.

## Implementation on PR #128
- PR: [#128](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/128), branch `feat/android-research-shadow-predictions`.
- Added isolated read-only API `GET /v1/research/predictions`, sourced only from `research_shadow_forecast_runs` and canonical fixture/team/competition identity tables.
- Existing `GET /v1/predictions` continues to read only published records and is unchanged.
- Android client fetches research forecasts separately, validates research-only/NOT_PUBLISHED/LOCKED flags, and presents them in the existing Home, BTTS and Over/Under screens. Each shadow fixture is visibly labelled `RESEARCH ONLY`; published fixture identities take precedence to avoid duplicates.
- Existing Android UI structure is preserved.
- Added automatic persistence after successful future shadow inference using the existing report validator and explicit isolated-ledger writer.
- Added a path-scoped one-time importer for the verified 21 November artifact (source run 44873166128), using the original source commit `5735b4126ea228c078d60af18e5b5b97dd6f86ca` for report identity. The writer is idempotent and inserts only into the append-only research ledger.
- No writes are made to production `predictions`, `published_predictions`, publication events, or settlement tables. No provider or Odds API requests are added.

## Verification status
- Branch and PR created successfully. The branch head at PR creation was `10afc80f07c153cfbe46cc05f8abd43b73d0d8dc`.
- PR metadata currently reports mergeable; the combined commit status showed a pending Vercel preview at last check. GitHub Actions CI completion has not yet been independently verified.
- Local offline artifact checks confirmed 25 forecasts, all five market distributions normalized, every forecast remains unpublished/value-locked, and each training cutoff < prediction cutoff <= generation time < kickoff.
- The production ledger schema was independently checked and contains the expected 14 columns. No ledger insert has yet been confirmed.
- The API endpoint, artifact import workflow, Android debug build, live Vercel deployment and physical-device display remain pending verification.

## Next steps
1. Wait for PR #128 backend tests/lint and Android debug build; fix any failures before merge.
2. Merge only after CI passes.
3. Verify the one-time artifact importer inserts exactly one research run with 25 forecasts and the expected report hash; confirm idempotency on duplicate execution if needed.
4. Verify `GET /v1/research/predictions` returns exactly the remaining upcoming forecasts with research-only flags and canonical fixture names.
5. Verify the Android app loads and displays the research fixtures on the existing screens; physical device test is required before claiming device-level success.
6. Confirm future shadow workflow runs persist each validated report to the research ledger.
7. Keep Stage 7 certification, production publication, model promotion and value betting locked until all independent certification gates pass.

## Evidence boundary
This is an implementation checkpoint, not a completed app deployment. No CI pass, merge, import, API response, APK installation, or physical-device rendering is claimed here until independently verified.
