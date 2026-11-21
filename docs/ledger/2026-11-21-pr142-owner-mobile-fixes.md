# 2026-11-21 — PR #142 owner-mobile workflow fixes

- Removed the two-parent merge requirement; retained 40-lowercase-hex validation and ancestor-of-main validation. Added an assertion that the audit implementation file exists in the checkout.
- ZIP SHA-256 values are logged for reference only; content hashes remain fatal. Artifact ID/name/expiry, ZIP integrity, expected filenames and single-JSON checks retained.
- Confirmed the `dev` optional extra in `backend/pyproject.toml`; root install `-e "backend[dev]"` matches CI's backend working-directory install `-e ".[dev]"`.
- Owner merge method may be squash, merge commit or rebase. After merge, use the main commit containing PR #142's changes.
- Phone instructions: GitHub app/browser → Actions → Corrected shrinkage audit → Run workflow; fill five inputs, run, then paste the run link here.
