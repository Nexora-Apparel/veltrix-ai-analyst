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

## Independent production verification after execution

Workflow run [#44117463950](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44117463950), job [#134159364294](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44117463950/job/134159364294), completed successfully and emitted `CANONICAL_INCREMENTAL_COMMITTED`.

The runner reported:
- Before: 21 canonical teams, one competition, 374 canonical fixtures and 374 fixture-source links.
- After: 21 canonical teams, one competition, 384 canonical fixtures and 384 fixture-source links.
- Ten fixtures created; 374 fixtures reused; no teams or competitions created.
- Ten run-5 fixtures linked; zero unlinked after execution.
- Review queue before and after: 28 cases / 28 events.
- Zero new identity-review events, zero PIT observations promoted, zero provider requests.

Independent Neon post-run queries confirmed:
- Provider fixtures: 384.
- Canonical teams / competitions / fixtures: 21 / 1 / 384.
- Team / competition / fixture-source links: 21 / 1 / 384.
- Unlinked provider fixtures: zero.
- Identity review cases / events: 28 / 28.
- PIT feature observations: zero.
- Exact source-observation and source-sighting provenance matches: 384 of 384.
- Duplicate provider-fixture source links: zero.
- Fixture-source mapping status: all 384 `REVIEW_REQUIRED`.
- Canonical fixture completeness: all 384 `SOURCE_ROW_ONLY`.
- Canonical fixture identity: 382 `IDENTITY_REVIEW_REQUIRED`, two `CONFLICT`.

No identity cases were approved or merged, no alias/reparenting/duplicate exclusion was activated, and no PIT features were promoted.

## Stage 2 exit boundary

**Stage 2 is complete for historical ingestion, provenance, canonical coverage and structural reconciliation.** The 28 identity cases remain human-pending and the two America MG identity-conflict rows remain unresolved. The source-publication/availability timestamp gap remains unresolved; no PIT feature engineering or model training using these rows is permitted.

The next stage may proceed with architecture/contracts and synthetic-only mathematical tests, but production training and predictions must remain gated until eligible PIT data and rights are independently established.
