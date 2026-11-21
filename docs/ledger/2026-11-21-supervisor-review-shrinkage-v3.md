# 2026-11-21 — Supervisor review and shrinkage repair v3

## Verified supervisor corrections
- Re-inspected sanitized artifact from run 44916186280 (artifact 14711832619). The archive includes fold-level dispersion, model metrics, climatology metrics, paired archived-minus-reference bootstrap results, fit convergence diagnostics, fold boundaries and team-effect ratio summaries.
- Corrected interpretation: no computed comparison favours archived; fold 1 vs k=2 and fold 4 vs k=0.5 significantly favour the references; two comparisons are unavailable due non-converged reference fits. Folds share expanding training data and are not independent.
- The JSON does not contain a per-team signal-survival metric, nor paired model-minus-climatology differences with confidence intervals. The existing team-ratio summaries are not signal-survival summaries and are not substituted.
- Fold test counts 158/115/217/161 (651 total) are counts of fixtures in the next 10% of unique kickoff-date windows, not 10% of fixture rows. Unequal fixture density per date explains variable counts.

## PR #142 caller-path verification
- Main's `backend/app/research/prospective_shadow.py` imports `fit_hierarchical_poisson` and calls it without an `optimizer` argument.
- The function default remains `optimizer="gradient_descent"`; the shadow caller supplies its existing half-life/team-ridge/competition-ridge constants (365/0.5/0.5). Therefore PR #142's added optional L-BFGS implementation does not change the default prospective-shadow fitting path.
- The shadow builder still labels output `SHADOW_ONLY_NOT_FOR_PUBLICATION`, `research_only=true`, `production_promotion=LOCKED`, `value_betting=LOCKED`, with `database_writes=0`. No PR #142 edit changes that route's quarantine behavior.
- CI delta in PR #142: add `.github/workflows/effective-shrinkage-audit.yml`, `docs/PROJECT_PROGRESS.md`, `docs/ledger/**`, and the audit preregistration document to both push and pull-request path filters; add an actionlint validation step for the effective-shrinkage audit workflow before pytest. No provider, deployment, database, feed, or lock operation is added by this CI change.

## Pre-registration v3 and draft repair
- Created draft PR #143: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/143
- Branch: `repair/damped-newton-prereg-v3`, based on main `25ca2d29927d3a48cf63bc6d6c451bbae5a4bf3b`.
- Added `docs/research/SHRINKAGE_REPAIR_PREREGISTRATION_V3.md` and `docs/research/shrinkage-selection-v3.json`.
- Frozen grid: k={0.25,0.5,1,2,4,8}; half-life={180,365,730} days. Selection restricted to development folds 1–3. Fold 4 (2026-10-28 to 2026-11-19) is explicitly disclosed as PREVIOUSLY_EXAMINED_DIAGNOSTIC_WINDOW and may only be used as a SHADOW-tier sanity check.
- Canonical config SHA-256: `80658db5ee8a8793e9c9d747101059072dd1fb3af55b08f6f610c4e5a6346a56`.
- PR #143 remains draft. Damped-Newton implementation, analytic Hessian/backtracking, synthetic equivalence tests, frozen candidate evaluation and prospective settlement scorer are pending. No solver change is claimed complete and no real-data run was started.

## Safety / controls
- Quarantine, production promotion, value-betting locks and feed state were not changed.
- No audit dispatch, real-data regularization/recovery run, provider call, Odds API call, database write, Telegram notification, merge, or production change was performed.
- Next: implement and test Newton on deterministic synthetic fixtures; only then extend the draft PR. Any merge or real-data dispatch remains owner-controlled.
