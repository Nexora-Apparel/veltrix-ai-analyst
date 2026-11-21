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
