# Round 38 canonical incremental materialization — implementation and verification

**Date:** 2026-11-17  
**Project:** VELTRIX AI ANALYST  
**Database:** `veltrix_ai_analyst`  
**Provider scope:** 5DollarFootballAPI / `5dollarfootballapi` / competition `522514093`  
**Import run:** 5  
**Implementation PR:** [#22](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/22)  
**Merge commit:** `1f45c1b3547d77d3127b84a111e3611e63efeb72`

## Import state

The controlled Round 38 import completed successfully in workflow run [#44107179999](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44107179999):
- Import run 5: COMPLETED.
- Requests: 2 of hard budget 4.
- New provider fixtures: 10; inserted: 10; duplicates/rejected/quarantined: 0.
- Provider fixture scope after import: 384 total; 380 FINISHED with scores; four UNKNOWN.
- PIT-certifiable features: zero.

## Incremental materializer

PR #22 adds:
- `backend/scripts/materialize_round38_incremental.py`
- `backend/tests/test_round38_incremental_materialization.py`
- `.github/workflows/materialize-round38-canonical-incremental.yml`

The workflow is manual-only and requires the exact input `MATERIALIZE_BRAZIL_SERIE_B_RUN_5_INCREMENTAL`. It checks the dedicated database name, exact starting table counts, exactly ten unlinked provider fixtures, all ten linked to import run 5, the full 384-fixture provenance-qualified plan, the existing known America identity collision, and exact post-write counts.

The runner uses the existing canonicalization materializer over the full source scope. This is intentional: all 374 existing canonical mappings are revalidated and reused, and only ten missing fixture-source mappings are created. It uses a SERIALIZABLE transaction and a dedicated advisory lock. It fails closed on any scope/count/provenance drift. It does not update provider projections, rewrite provenance, approve identity cases, create identity-review decisions, promote PIT features, or call the provider.

## Validation

CI workflow run [#44116261032](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44116261032) completed successfully:
- Backend: 122 tests passed.
- Ruff: all checks passed.
- Android debug build: passed.
- APK artifact: `veltrix-ai-analyst-debug-apk`, SHA-256 `3b347e0f63dc83f992bedf3e62d12ff198b15de5f646071f73fcf8bfad6dda80`, retained until 2026-11-24.

## Independent production read-only checks before execution

Neon production queries confirmed:
- 384 provider fixtures in scope.
- 374 already-linked fixtures have exact source-observation and earliest matching source-sighting provenance.
- Zero existing fixture source-sighting mismatches.
- All 21 team identity links match their current source-observation and earliest matching source-sighting provenance.
- The competition identity link matches its source-observation and earliest matching source-sighting provenance.
- Exactly 10 fixtures are currently unlinked.
- Review queue remains 28 cases and 28 case events.

These are read-only checks. The 10 canonical links have **not** yet been written.

## Manual execution blocker

This session can inspect and update GitHub repository files but has no GitHub Actions workflow-dispatch operation. No production materialization was attempted.

After confirming PR #22 is merged and the main-branch workflow is available:
1. Open [Materialize Round 38 canonical fixtures](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/materialize-round38-canonical-incremental.yml).
2. Select **Run workflow**.
3. Set `confirm_materialization` to `MATERIALIZE_BRAZIL_SERIE_B_RUN_5_INCREMENTAL`.
4. Inspect the sanitized JSON result and require `CANONICAL_INCREMENTAL_COMMITTED`.

After dispatch, independently verify 21 canonical teams, one canonical competition, 384 canonical fixtures, 21 team links, one competition link, 384 fixture-source links, zero unlinked provider fixtures, and unchanged review-case/event counts (28/28). Confirm all 384 source links remain `REVIEW_REQUIRED`, all canonical fixtures remain `SOURCE_ROW_ONLY`, and no PIT features were promoted.

## Stage 2 exit boundary

Stage 2 remains open until the manual incremental workflow succeeds and production counts are independently verified. The 28 identity cases remain human-pending. The source-publication/availability timestamp gap remains unresolved; zero PIT feature promotion and zero model training remain mandatory. Stage 3 must not start using these historical rows as pre-match training features.
