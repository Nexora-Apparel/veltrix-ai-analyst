# 2026-11-21 — PR #142 owner-mobile workflow fixes

- Removed the two-parent merge requirement; retained 40-lowercase-hex validation and ancestor-of-main validation. Added an assertion that the audit implementation file exists in the checkout.
- ZIP SHA-256 values are logged for reference only; content hashes remain fatal. Artifact ID/name/expiry, ZIP integrity, expected filenames and single-JSON checks retained.
- Confirmed the `dev` optional extra in `backend/pyproject.toml`; root install `-e "backend[dev]"` matches CI's backend working-directory install `-e ".[dev]"`.
- Owner merge method may be squash, merge commit or rebase. After merge, use the main commit containing PR #142's changes.
- Phone instructions: GitHub app/browser → Actions → Corrected shrinkage audit → Run workflow; fill five inputs, run, then paste the run link here.

## Post-merge verification — 2026-11-21

- PR #142 merged successfully using squash after final exact-head verification. PR state is closed/merged; head was `469097b58c1fce2d58b6684bbb1b504b512fcfba`; resulting main commit is `4ee0cbfdcb98149524c0a7a369fc0400126b4c6f`.
- Exact-head CI run [44902828715](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44902828715): actionlint passed; backend tests **510 passed, 1 warning**; Ruff passed; Android debug build passed and APK artifact [14706244340](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44902828715/artifacts/14706244340) uploaded (16,461,005 bytes). Android has a non-blocking deprecated `Icons.Filled.TrendingUp` warning.
- Re-checked PR immediately before merge: open, ready (not draft), mergeable, exact head unchanged, no review threads; required CI run was successful. Full 9-file PR diff reviewed. Vercel preview is Ready; earlier daily deployment quota failures were not retried.
- Re-fetched the workflow from `main`: manual `workflow_dispatch` only; 40-lowercase-hex SHA validation, ancestor-of-main validation and audit implementation-file assertion retained. Obsolete two-parent restriction is absent. ZIP byte SHA-256 values are logged only; dataset and canonical training-data fingerprints remain fatal.
- The previous Commit C notes above that say “two-parent PR merge commit” and “ZIP hashes verified” are superseded by the actual merged workflow and this post-merge verification. Squash, merge-commit and rebase histories are supported.
- Main commit containing the implementation for the audit input is `4ee0cbfdcb98149524c0a7a369fc0400126b4c6f`. This is the value to use for `audit_commit_sha` if/when the owner manually dispatches.
- **No audit dispatch occurred.** No 996-row dataset was loaded, fitted or evaluated by this workflow. Quarantine, production publication and value-betting locks remain unchanged. Do not dispatch until the user explicitly authorizes it after reviewing the 996-match evidence.


## Corrected shrinkage audit execution — 2026-11-21

- Owner-corrected workflow run [44916186280](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44916186280), job [136882181793](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44916186280/job/136882181793): all 11 job steps completed successfully, including exact commit checkout, main ancestry validation, source artifact retrieval, source fingerprint verification, audit tests, sanitized report generation and artifact upload.
- Exact audit implementation commit checked out: `4ee0cbfdcb98149524c0a7a369fc0400126b4c6f`. Dataset SHA matched `80148b3f0f42e70d94391d9283c42f35b5b92e1631a9a1cb7baee899373dad0c`; canonical training-data SHA matched `d70ee34940c8fc6681f3cd5751d4fdcc2e876b307fe388d9f3a792c73e34b262`. Audit tests: **18 passed**.
- Sanitized artifact: [14711832619](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44916186280/artifacts/14711832619), `veltrix-corrected-shrinkage-audit-json`, 70,655 bytes; downloaded and inspected. It contains only the allowlisted sanitized JSON.
- Audit status is `DIAGNOSTIC_ONLY`; admission conclusion is `NONE: corpus is not point-in-time certified`; production promotion and value betting remain `LOCKED`. The report confirms 996 training rows and 25 archived forecasts. No production write or lock change occurred.
- Four chronological folds tested 651 fixtures in total (158, 115, 217, 161). Low-history test counts were 127, 66, 27 and 0. Archived fit converged in all four folds. Reference fit convergence was incomplete: k=0.5 did not converge in fold 1; k=2.0 did not converge in fold 4. Those comparisons were not computed.
- On converged comparisons, archived-minus-reference paired log-loss differences were: fold 1 vs k=2.0 **+0.0734** (95% date-block CI +0.0394 to +0.1131); fold 2 vs k=0.5 **−0.0396** (CI −0.1329 to +0.1360), vs k=2.0 **+0.0110** (CI −0.0551 to +0.1176); fold 3 vs k=0.5 **−0.0236** (CI −0.0801 to +0.0282), vs k=2.0 **+0.0148** (CI −0.0239 to +0.0493); fold 4 vs k=0.5 **+0.1092** (CI +0.0509 to +0.1520). Positive values mean archived fit has worse log loss. Results are mixed; confidence intervals include zero in most comparisons.
- **Interpretation:** this is not evidence to promote either model. The reference fits are not fully converged across all folds, and the corpus is explicitly not point-in-time certified. The audit remains diagnostic only. Do not begin the separate real-data regularization/recovery tests until the user has reviewed the 996-row dataset evidence.
- The earlier run [44903178556](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44903178556) failed before any data access because the checkout ref was passed as the literal string `audit_commit_sha`; the corrected run above successfully checked out the exact SHA. No dataset evaluation occurred in the failed attempt.
