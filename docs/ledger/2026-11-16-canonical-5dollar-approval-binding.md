# Canonical 5Dollar approval binding corrected — 2026-11-16

## Finding
Before any historical import, review found that the importer derived a second approval ID instead of referencing the exact registered 5Dollar Community approval verified by the read-only preflight. No live collection request had been made.

## Correction
- PR [#8](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/8) merged to `main`.
- Merge commit: `71eedf3abeedcd0312d7f7038b5e9541b7af5484`.
- Importer now uses `FIVEDOLLAR_COMMUNITY_APPROVAL` directly.
- Canonical approval ID: `approval-5dollar-community-fixtures-2026-11-12`.
- Added regression test asserting exact approval ID, provider, source, competition scope and fixtures/results data type.
- Collection plan and progress register updated to prohibit a derived duplicate approval record.

## Validation
- CI run [#43952346445](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43952346445) completed successfully.
- Backend tests: passed.
- Ruff lint: passed.
- Android debug build: passed.
- APK artifact upload: passed.
- A read-only Neon query independently confirmed the canonical approval row's full evidence fields match the source approval definition used by the importer.

## Safety state
- Provider HTTP requests for the historical collection: 0.
- Historical fixture rows imported: 0.
- Odds requests: 0.
- Live collection remains LOCKED pending an explicit separate authorization from the user. The successful preflight and merged code correction do not themselves dispatch the collection workflow.
