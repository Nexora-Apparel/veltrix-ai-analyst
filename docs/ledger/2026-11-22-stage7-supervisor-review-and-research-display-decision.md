# 2026-11-22 — Stage 7 run #44999986842 supervisor review and research-display decision

## Source-of-truth state

- Repository: `Nexora-Apparel/veltrix-ai-analyst`.
- Verified `main` HEAD at review: `760eb0df0bd88fdd06eb105ab9b3c982db3fd70a` (PR #148 merge).
- Stage 7 manual workflow run: [44999986842](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44999986842), job `137139190778`.
- Run conclusion: success; model `hierarchical-poisson-newton-shadow-v2`; 21 forecasts; monitor PASS.
- Artifact: [14745790831](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44999986842/artifacts/14745790831).
- Isolated research-ledger run key: `cf87118887071568e5d4279f7a82190cce697790265f56adff47a61957b3323b`.
- Read-only Neon query confirmed exactly one `research_shadow_forecast_runs` row for that key: model version `hierarchical-poisson-newton-shadow-v2`, status `SHADOW_FORECASTS_READY`, forecast_count 21, generated_at `2026-11-22T07:51:24.747Z`.
- No inference, persistence, provider call, Odds API call, deployment, environment change, or app/display change was performed during this supervisor review.

## Supervisor assessment accepted

The supervisor accepted the 21-fixture forecast table, corrected 1X2 concentration calculations, model diagnostics, and database row confirmation.

- The 21 forecasts were differentiated; all team/competition names resolved; no duplicate fixtures were identified.
- Supervisor assessment: major favourites and away favourites were plausible on this slate; draw probabilities ranged approximately 9–35%.
- P(home) mean 0.489 and SD 0.178 are above the development-fold reference ranges (mean 0.42–0.46; SD 0.13–0.16), but within the configured monitor limits (P(home) SD 0.08–0.22).
- 1X2 top-pick concentration was 76.2%, below the 85% monitor limit. BTTS-yes and Over-2.5 top-pick shares were each approximately 61.9%, below their 90% limits.
- Corrected 1X2-only threshold counts: any 1X2 outcome >0.80 in 1/21 fixtures; any 1X2 outcome >0.70 in 2/21 fixtures. The sanitized `any_probability_above_080_share` is an all-market statistic and must not be represented as 1X2-only.
- The supervisor confirms training fingerprint `d70ee34940c8fc6681f3cd5751d4fdcc2e876b307fe388d9f3a792c73e34b262` is the frozen training fingerprint used since the first audit.

## Caveats to retain with any research display

1. European teams have only 9–13 training matches per team in this fit; team-strength estimates are rough.
2. Goal totals appear high in several fixtures: Augsburg–Mainz approximately 4.8 expected goals; Barcelona–Villarreal approximately 4.7; Racing Santander–Real Sociedad approximately 4.3; Monza–Fiorentina approximately 4.1. Slate mean is approximately 3.1 expected goals. Werder Bremen home-win probability is approximately 72%; Barcelona home-win probability approximately 85%. These may be overconfident, consistent with the 4–7 percentage-point favourite overconfidence observed in development folds. This is a caution, not a new calibration conclusion.
3. Training cutoff is `2026-11-19T05:40:39.619310+00:00`; results settled after that cutoff are not included in this fit.
4. The run remains `RETROSPECTIVE_NOT_PIT_CERTIFIED`. No accuracy claim is permitted.

## Decision — research-only display approved conditionally

- Supervisor approves owner-controlled research-only display, labelled `RESEARCH ONLY`.
- This approval is conditional on the owner setting `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED=true` in the production deployment environment and performing the redeploy.
- Assistant must not set the environment variable, redeploy, or otherwise change deployment/display state.
- After the owner confirms that the flag has been set and the redeploy completed, perform read-only production verification against `https://veltrix-ai-analyst-api.vercel.app`:
  1. GET `/v1/research/predictions`; record HTTP status and response body fields: status, model_version, forecast count (which may be below 21 after kickoffs), research-label fields, and verify no v1 forecasts appear.
  2. Verify the model-version-matched admission record file is present in the deployed bundle. If response reports `MODEL_QUARANTINED` or admission error, inspect route code and identify the exact cause.
  3. GET `/v1/predictions`; confirm zero published predictions.
  4. Compare Barcelona–Villarreal, Hull–Brighton, and Liverpool–Man Utd response probabilities with the reviewed Stage 7 table, accounting for fixtures that have kicked off and any expected filtering.
  5. Inspect the existing Android app integration and report what its three screens read; verify the app's `RESEARCH ONLY` badge is bound to the response label. Preserve existing UI.
- Until that owner action occurs, no production API read-back or Android feed verification is claimed.

## Locks and deferred work

- Production promotion remains `LOCKED`.
- Value betting remains `LOCKED`.
- No accuracy claims.
- The following follow-ups are explicitly non-blocking and must not start until the owner confirms the app displays the research feed. They are to be handled together in one PR:
  1. Record config hash and admission-record hash in the report model block.
  2. Include settled prospective labels in training with strict point-in-time cutoffs.
  3. Add fixture-level abstention-subset diagnostics.
  4. Compare goal-total inflation against development folds, including expected-goals mean and SD for the selected configuration.
  5. Then proceed to automation work.
- Do not start these follow-ups before the owner's app-display confirmation.

## Actions in this entry

- This entry records the supervisor's assessment, caveats, conditional owner-controlled research-display approval, verification checklist, and deferred follow-ups.
- No application code, production configuration, database rows, workflows, schedules, Android UI, or deployment state was changed.
