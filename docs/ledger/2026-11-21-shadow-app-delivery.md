# 2026-11-21 — Research forecasts integrated into Android

## Delivery checkpoint
- PR #128 merged: `e5b803ba2abd72a64b895ceb4134418d09f3c605`.
- CI run `44874754638` succeeded: backend tests/lint and Android debug build.
- Production Vercel deployment READY on commit `e5b803ba2abd72a64b895ceb4134418d09f3c605`.
- APK artifact `14695247214`, SHA-256 `3905258c475d1029313b3e0102c50f094dc37281f66ade6ed32b13c3ee4528cb`.
- Android APK built successfully; physical installation and UI verification not yet done.

## Research run import verification
- Research ledger row count read-only query: 1.
- Latest run key: `8313d814c870845f1fa08fe2810529f6c26bde9feaa71f1d6d748218098fef89`.
- Generated: `2026-11-21T05:59:20.681Z`.
- Status: `SHADOW_FORECASTS_READY`.
- Training labels: 996 (historical training data, not prospective settled selections).
- Forecasts in report: 25.
- Model version: `hierarchical-poisson-shadow-v1`.
- `research_only=true`; value betting locked.
- Read-only eligible upcoming fixture count: 25; 23 today, 2 tomorrow. Earliest kickoff `2026-11-21T12:30:00Z`; latest `2026-11-22T11:30:00Z`.
- These are ledger and query checks. Direct live API response and physical Android display are still pending.

## Architecture and release boundary
- Isolated `GET /v1/research/predictions` API reads only the append-only research ledger.
- Android loads forecasts on the existing screen structure and marks shadow forecasts `RESEARCH ONLY`; published fixtures take precedence when deduplicating.
- Existing production prediction and publication tables are not used for shadow forecasts.
- Research forecasts remain unpublished; certification, production promotion and value betting remain locked.

## Remaining validation
1. Install APK and verify app connectivity, fixture display, markets and research label on a physical Android device.
2. Independently verify direct endpoint response and HTTP status.
3. Verify next daily shadow workflow inserts its report in ledger.
4. Keep production certification gates unchanged.
