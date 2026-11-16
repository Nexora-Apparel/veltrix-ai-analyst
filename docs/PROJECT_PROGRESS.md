# VELTRIX AI ANALYST — Project Progress Register

> Canonical execution tracker for the VELTRIX AI ANALYST project. Update this document whenever implementation status, scope, decisions, blockers, or validation evidence changes.

**Last updated:** 2026-11-16  
**Repository:** https://github.com/Nexora-Apparel/veltrix-ai-analyst  
**Default branch:** `main`  
**Repository visibility:** Public  
**Product:** Personal-use, cloud-backed native Android football analysis and prediction application

## 1. Executive status

- **Overall stage:** Stage 2 of 10 — Data integrations and historical data migration
- **Current workstream:** Stage 2 provider adapters, source-rights enforcement, historical qualification, private snapshot capture and PostgreSQL persistence foundation.
- **Implementation status:** Stage 1 is complete. Provider adapters, rights evaluation, pinned AI Midas snapshot capture, exact source approvals, and a provenance-first PostgreSQL schema/migration runner are implemented. The database foundation is under PR #1; its CI validation is pending.
- **Release status:** Not deployed. No production database, live provider import, authentication, or prediction functionality exists yet.
- **Next milestone:** Obtain a clean CI pass, verify the new repository's 5Dollar Community credential, then build the rights-aware historical ingestion and persistence layer.

## 2. What is established

The following decisions and project foundations have been established:

- [x] Project name: **VELTRIX AI ANALYST**.
- [x] New repository created: `Nexora-Apparel/veltrix-ai-analyst`.
- [x] Repository verified as **public**; public source and documentation are intentional.
- [x] Product target: native Android application, not a web-only product.
- [x] Personal-use scope; avoid SaaS billing, customer management, advertising systems, and unnecessary commercial infrastructure.
- [x] Global football coverage objective, subject to real provider coverage and transparent data-quality restrictions.
- [x] Cloud-backed architecture: heavy ingestion, research, and model computation run on the backend; Android is the user-facing client.
- [x] Prediction intelligence will be built independently from scratch.
- [x] Selective reuse is allowed only for inspected, proven provider adapters, data utilities, CI patterns, and infrastructure patterns.
- [x] Secrets, API keys, passwords, private user data, and production credentials must never be committed to this public repository.
- [x] No unsupported league, market, model, or accuracy claims. Evidence and validation are required before publication.

## 3. Ten-stage delivery roadmap

| Stage | Name | Scope / exit condition | Status |
|---|---|---|---|
| 1 | Architecture and repository foundation | Document architecture, security/data rules, repo structure, development workflow, and establish tested Android/backend skeletons. | **COMPLETED** |
| 2 | Data integrations and historical migration | Implement provider adapters, ingestion, normalization, provenance, deduplication, incremental sync, caching, and validated historical import. | **IN PROGRESS** |
| 3 | Football intelligence | Build reliable team, player, competition, fixture, form, availability, and match-context representations. | NOT STARTED |
| 4 | New statistical prediction engine | Develop and independently evaluate goal and outcome models, features, probability generation, and calibration. | NOT STARTED |
| 5 | AI research and tactical intelligence | Add evidence-grounded research for lineups, injuries, tactics, schedule load, travel, and material data gaps. | NOT STARTED |
| 6 | Multi-market prediction engine | Add market-specific calculations and publication gates for supported markets. | NOT STARTED |
| 7 | Backtesting, validation and certification | Run chronological walk-forward tests, leakage checks, calibration and market-level certification; document limitations. | NOT STARTED |
| 8 | Native Android application | Deliver Compose UI, authentication, fixtures, match analysis, predictions, history, settings, and resilient API/offline behaviour. | NOT STARTED |
| 9 | Paper prediction tracking | Persist immutable forecasts, settle outcomes, track performance, and compare predictions with appropriate baselines. | NOT STARTED |
| 10 | Private production deployment | Deploy secured cloud services and database, configure backups/monitoring, connect the Android client, and complete release checks. | NOT STARTED |

A stage is not complete merely because files exist. Its exit condition must be met and supported by tests, reports, or other verifiable evidence.

## 4. Current work — Stage 2

### Stage 1 — COMPLETED
- [x] Repository created and verified; public visibility confirmed.
- [x] Product scope, native Android direction, ten-stage roadmap, and reuse boundary established.
- [x] Public-repository secret-handling rules and security policy committed.
- [x] Root README, architecture document, and canonical progress register committed.
- [x] FastAPI liveness endpoint and health tests committed.
- [x] Kotlin/Jetpack Compose Android foundation and initial screen committed.
- [x] GitHub Actions CI committed for backend tests/lint and Android debug APK.
- [x] CI runs #43853169748 and #43853312298 passed backend tests/lint and Android debug compilation.
- [x] Stage 2 CI run #43856574834 passed 21 backend tests, Ruff lint, Android debug APK compilation and artifact upload.
- [x] Backend tests passed 40/40 in CI run #43857128747; its Ruff step found an import-formatting issue that has been corrected.
- [ ] Pass PR #1 PostgreSQL migration integration tests, Ruff lint and Android build.

### Stage 2 — CURRENT WORK
- [x] Provider-neutral source-provenance, competition and fixture contracts with timezone-aware timestamps and settled-score invariants.
- [x] 5DollarFootballAPI adapter for account status, competition discovery, fixtures/results, pagination, rate-limit handling and moved competition IDs.
- [x] League-specific historical endpoint used for bounded competition backfills; global endpoint is split into maximum 24-hour windows.
- [x] Mocked tests for 5Dollar authentication, pagination, results, account status, rate limits, moved IDs, window boundaries and unsettled-score handling.
- [x] Fail-closed rights evaluator: exact source scope, permitted use, approval validity, non-commercial restrictions, attribution and raw-redistribution controls.
- [x] AI Midas pinned Brazil Serie B 2026 snapshot collector with Git blob/SHA-256, row, match, team, date-range and score-orientation validation.
- [x] Source score anomalies are quarantined at match level rather than silently accepted; direct inspection found one inconsistent match (two rows), leaving 368 other matches as candidates for further validation.
- [x] Raw AI Midas snapshots are restricted to private/local paths outside the public repository; the collector records a rights/provenance manifest and makes no database/model writes.
- [x] Provider qualification register updated with prior account evidence, rights conditions, source limitations and reuse decisions.
- [x] Manual 5Dollar account-access workflow and local AI Midas snapshot command committed.
- [x] PostgreSQL provenance-first schema migration and checksum-verified runner added on PR #1.
- [x] Migration runner requires an explicit expected database name and blocks legacy VELTRIX Football database names.
- [x] CI configured with an ephemeral PostgreSQL 16 service and migration integration tests.
- [ ] Verify PR #1 migration SQL, integration tests, lint and Android build; merge only after all checks pass.
- [ ] Configure the existing 5Dollar Community credential as a repository secret and run the manual access check.
- [ ] Capture the pinned AI Midas file locally and verify the actual source hash.
- [ ] Design and implement rights-aware persistence, immutable source evidence, import manifests, checkpoints and quarantine.
- [ ] Implement bounded incremental historical ingestion only after database and provider checks are complete.

### Not yet built
- Android authentication, API integration, navigation, local persistence, and product screens.
- FastAPI authentication and domain APIs.
- A provisioned PostgreSQL instance and a production connection; the schema/migration foundation exists but is not deployed.
- Runtime database writers and an actual private PostgreSQL instance; the schema and migration runner are in PR #1.
- Live 5Dollar provider qualification from the new repository.
- Historical AI Midas snapshot capture and private persistence.
- Additional odds-provider integration and timestamp qualification.
- Football intelligence and feature pipelines.
- Statistical models, calibration, and consensus logic.
- AI research orchestration.
- Market-specific prediction modules.
- Backtesting/certification suite.
- Paper-trading ledger and settlement.
- Production deployment, monitoring, and backups.

## 5. Target architecture

- **Android client:** Kotlin, Jetpack Compose, MVVM, Clean Architecture, Hilt, Retrofit/OkHttp, Room, and WorkManager where justified.
- **Backend API:** Python, FastAPI, Pydantic, authenticated REST endpoints.
- **Persistence:** PostgreSQL as the system of record.
- **Cache/queue:** Redis only where measured workload requires it.
- **Workers:** Lightweight background workers initially; introduce a task queue only when needed.
- **Modelling:** Python with transparent, testable numerical components; SciPy and scikit-learn where appropriate.
- **Operations:** Docker, GitHub Actions, structured logs, health checks, backups, and controlled deployment.
- **Cloud execution:** Data ingestion, research, and prediction computation run remotely; Android consumes authenticated APIs.
- **Cost discipline:** Prefer caching, incremental sync, deduplication, and selective research over repeated provider calls or indiscriminate LLM usage.

Technology choices may be revised when implementation evidence justifies the change. Avoid adding infrastructure without a demonstrated need.

## 6. Prediction-engine independence rules

The following must be newly designed, implemented, tested, and validated for this project:

- Match outcome and goal probability calculations.
- Team-strength estimation and prediction feature engineering.
- Probability calibration and uncertainty handling.
- AI consensus and decision logic.
- Confidence scoring, value detection, and market publication gates.
- Model weights, thresholds, and prediction decision rules.

Do **not** copy legacy prediction models, fallback priors, trained weights, calibration parameters, or decision rules from VELTRIX FOOTBALL 2.0 or any other project. Historical raw data may be imported only after provenance, licensing/terms, timestamp, schema, and quality checks. Data is not a model.

Candidate methods such as Poisson, Dixon–Coles, Elo, and other approaches are hypotheses, not pre-approved winners. Select methods using chronological out-of-sample evidence.

## 7. Data coverage and publication policy

- Global coverage is an objective, not a promise of equal data quality across every competition.
- Assign transparent competition/data-quality tiers: **Tier A** (strong), **Tier B** (usable with limitations), **Tier C** (limited), and **Restricted** (insufficient evidence for publication).
- Never fabricate missing statistics, lineups, odds, or source timestamps.
- Store source identity, retrieval time, source event time where available, raw/normalized provenance, and data-quality flags.
- Enforce market-specific data sufficiency and validation gates. A match being available does not mean every market is publishable.
- LLM-generated explanations must cite or reference verified inputs and must never invent statistics or probabilities.
- Keep forecasts immutable once issued; corrections or recalculations must be versioned and traceable.

## 8. Reuse register

Potentially reusable components are **candidates for inspection**, not approved dependencies. Reuse requires code review, licence/terms review, tests, and isolation behind adapters.

| Component/source | Intended treatment | Guardrail |
|---|---|---|
| 5DollarFootballAPI | New isolated adapter; prior account evidence and seven entitled competitions inspected. | Old account qualification: 2,496 finished fixtures, 26 pages, 28/40 requests, zero duplicates/rejections. Recheck new repo credentials before importing; do not repeat a full history pull unnecessarily. |
| AI Midas | New pinned single-file snapshot collector for Brazil Serie B 2026. | Non-commercial only, attribution required, raw redistribution prohibited; 738 team rows / 369 matches / 20 teams; no publication timestamp and not point-in-time certifiable. |
| Historical football data | Reuse only source-approved raw data and generic ingestion patterns. | Prior Neon database had zero match rows; a 70,444-row Football-Data/ClubElo CSV remains quarantined and must not be imported. |
| Odds data | 5Dollar and AI Midas odds remain supplemental candidates only. | 5Dollar Community historical odds tick endpoint was HTTP 403 in prior qualification; AI Midas average odds have no verified quote timestamps. Neither is CLV-certified. |
| Odds-provider patterns | Inspect and adapt provider adapters. | Do not assume odds are closing odds or point-in-time valid without evidence. |
| Team/competition/fixture normalization | Reuse only after inspection and tests. | Keep canonical IDs and aliases auditable. |
| Results tracking and reporting utilities | Reuse generic utilities if independent of legacy prediction logic. | Reconcile settlements and prevent duplicate results. |
| GitHub Actions and security patterns | Reuse workflow patterns after review. | No secrets in source, logs, artifacts, or public CI output. |
| Legacy prediction code/models | **Do not reuse.** | Rebuild the entire prediction intelligence independently. |
| Telegram and legacy website | Not part of the initial product scope. | Native Android is the product interface. |

## 9. Validation and release gates

No model or market is production-certified until its evaluation protocol, data coverage, sample size, baselines, and results are documented. Required controls include:

- Chronological train/validation/test separation and walk-forward evaluation.
- Point-in-time feature construction; no future-data leakage.
- Reproducible dataset snapshots and model/version identifiers.
- Calibration and proper scoring rules, with uncertainty reported.
- Market-specific performance and sufficient sample sizes.
- Odds provenance and timestamp verification wherever value or CLV claims are made.
- Prospective paper tracking before any live recommendation is described as validated.
- Explicit restricted/no-prediction outcomes when evidence is insufficient.

No accuracy, profitability, or positive-ROI claim is permitted without independently reproducible evidence.

## 10. Decision log

| Date | Decision |
|---|---|
| 2026-11-16 | Confirmed the project roadmap contains ten stages and this file is the canonical progress register. |
| 2026-11-16 | Repository is public by explicit project decision; credentials and private data remain excluded. |
| 2026-11-16 | Product is a personal-use, cloud-backed native Android app. |
| 2026-11-16 | Prediction intelligence will be rebuilt from scratch; only inspected non-prediction infrastructure/data utilities may be reused. |
| 2026-11-16 | Initial FastAPI, Android Compose, CI, security, README, and architecture foundations committed to main. |
| 2026-11-16 | Stage 1 passed backend tests/lint and Android debug compilation in CI runs #43853169748 and #43853312298; Stage 1 marked complete and Stage 2 started. |
| 2026-11-16 | 5Dollar account evidence from the prior VELTRIX project is reused as a baseline; the new repository accepts the established secret names and does not repeat a full historical pull. |
| 2026-11-16 | AI Midas Brazil Serie B 2026 is treated as a pinned non-commercial CSV source; raw data stays outside the public repository and remains non-PIT. |
| 2026-11-16 | A row-level score mismatch was detected in one AI Midas match; the snapshot collector quarantines the full match instead of trusting inconsistent goals. |
| 2026-11-16 | PostgreSQL ingestion schema is isolated under `veltrix_ai_analyst`; migrations require an explicit expected database name and block legacy VELTRIX Football database names. |
| 2026-11-16 | PR #1 opened for PostgreSQL 16 migration validation; no database provisioning or historical import is part of the PR. |

Add new decisions with dates. Do not silently overwrite material architectural decisions; record the reason for changes.

## 11. Blockers and risks

- **Manual credential step:** the new repository still needs the 5Dollar Community key added as a GitHub Actions secret named `FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY` (or `FIVEDOLLARFOOTBALL_API_KEY`). The value must not be sent in chat or committed. The manual workflow is ready.
- **AI Midas availability:** the pinned CSV is publicly retrievable without an API key, but its actual snapshot has not yet been captured in this environment or persisted to a private database.
- **Point-in-time limitation:** AI Midas Brazil Serie B team statistics have no verified publication timestamp and cannot be treated as pre-match features.
- **Source anomaly:** one AI Midas Brazil Serie B match has inconsistent row-level scores; the collector quarantines that match.
- **Odds limitation:** neither the 5Dollar Community historical odds endpoint nor the AI Midas average-odds fields are currently certified for bookmaker-specific closing-price or CLV analysis.
- **Database not provisioned:** the new schema and migration runner are in PR #1, but no database has been provisioned or connected. Do not reuse the old Neon database; prior Phase 2 evidence reports zero historical match rows and a quota-exceeded connection during a separate AI Midas reconciliation.
- **Incomplete product implementation:** current backend and Android code are foundations, not a working football analysis application.
- **Global coverage:** quality will vary; restricted competitions must remain unpublished until evidence improves.
- **Cost/quota control:** use the existing 5Dollar historical qualification as baseline, then incremental sync, caching, deduplication and explicit request budgets.

## 12. Next execution queue

1. Get a clean CI pass for the latest rights and settled-score changes.
2. Add the existing 5Dollar Community credential to the new repository secrets and run the manual account/league check.
3. Run the AI Midas snapshot command locally to capture and verify the pinned Brazil Serie B file; keep it under `.local-data/`.
4. Complete and merge PR #1 after PostgreSQL 16 integration tests, lint and Android CI pass.
5. Provision a new private PostgreSQL database only after a connection target and credentials are configured; never reuse the legacy database.
6. Connect the persistence layer to the source approvals, provider responses, entitlement observations, immutable source observations, import manifests, checkpoints and quarantine.
7. Implement bounded historical import for the seven already-qualified 5Dollar competitions, subject to current account recheck.
8. Add AI Midas data to private storage as non-commercial, non-PIT historical evidence; keep its post-match stats out of pre-match feature sets until availability is proven.

## 13. Update protocol

For every meaningful implementation session:
1. Update **Last updated**.
2. Record exact files/modules added or changed.
3. Record tests/builds run and their actual outcomes.
4. Update stage and task statuses.
5. Record commit/PR identifiers where available.
6. Add blockers, decisions, and next tasks.
7. Never mark a task complete based only on an intention or an unverified claim.

This file is the canonical project progress record. Keep it current as the project evolves.
