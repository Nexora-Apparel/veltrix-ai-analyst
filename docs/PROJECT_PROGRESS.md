# VELTRIX AI ANALYST — Project Progress Register

> Canonical execution tracker for the VELTRIX AI ANALYST project. Update this document whenever implementation status, scope, decisions, blockers, or validation evidence changes.

**Last updated:** 2026-11-16  
**Repository:** https://github.com/Nexora-Apparel/veltrix-ai-analyst  
**Default branch:** `main`  
**Repository visibility:** Public  
**Product:** Personal-use, cloud-backed native Android football analysis and prediction application

## 1. Executive status

- **Overall stage:** Stage 1 of 10 — Architecture and repository foundation
- **Current workstream:** Initial backend and native Android foundations, repository security rules, architecture documentation, and CI setup.
- **Implementation status:** Initial FastAPI liveness endpoint and test, Kotlin/Jetpack Compose Android placeholder app, Gradle configuration, CI workflow, security policy, and architecture documentation have been committed. CI/build execution has not yet been verified.
- **Release status:** Not deployed. No database, provider integrations, authentication, or prediction functionality exists yet.
- **Next milestone:** Verify CI and builds, fix any failures, then complete Stage 1 exit criteria.

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
| 1 | Architecture and repository foundation | Document architecture, security/data rules, repo structure, development workflow, and establish tested Android/backend skeletons. | **IN PROGRESS** |
| 2 | Data integrations and historical migration | Implement provider adapters, ingestion, normalization, provenance, deduplication, incremental sync, caching, and validated historical import. | NOT STARTED |
| 3 | Football intelligence | Build reliable team, player, competition, fixture, form, availability, and match-context representations. | NOT STARTED |
| 4 | New statistical prediction engine | Develop and independently evaluate goal and outcome models, features, probability generation, and calibration. | NOT STARTED |
| 5 | AI research and tactical intelligence | Add evidence-grounded research for lineups, injuries, tactics, schedule load, travel, and material data gaps. | NOT STARTED |
| 6 | Multi-market prediction engine | Add market-specific calculations and publication gates for supported markets. | NOT STARTED |
| 7 | Backtesting, validation and certification | Run chronological walk-forward tests, leakage checks, calibration and market-level certification; document limitations. | NOT STARTED |
| 8 | Native Android application | Deliver Compose UI, authentication, fixtures, match analysis, predictions, history, settings, and resilient API/offline behaviour. | NOT STARTED |
| 9 | Paper prediction tracking | Persist immutable forecasts, settle outcomes, track performance, and compare predictions with appropriate baselines. | NOT STARTED |
| 10 | Private production deployment | Deploy secured cloud services and database, configure backups/monitoring, connect the Android client, and complete release checks. | NOT STARTED |

A stage is not complete merely because files exist. Its exit condition must be met and supported by tests, reports, or other verifiable evidence.

## 4. Current work — Stage 1

### Completed within Stage 1
- [x] Repository created and verified; public visibility confirmed.
- [x] Product scope, native Android direction, ten-stage roadmap, and reuse boundary established.
- [x] Public-repository secret-handling rules and security policy committed.
- [x] Root README, architecture document, and canonical progress register committed.
- [x] FastAPI application skeleton with liveness endpoint and health tests committed.
- [x] Kotlin/Jetpack Compose Android application skeleton and initial screen committed.
- [x] GitHub Actions workflow committed for backend tests/lint and Android debug build.

### In progress
- [ ] Observe CI workflow results and resolve any backend or Android build failures.
- [ ] Verify the repository tree and confirm the Android build is reproducible.
- [ ] Add backend configuration conventions and API contract tests as needed.
- [ ] Complete Stage 1 exit review after successful verification.

### Not yet built
- Android authentication, API integration, navigation, local persistence, and product screens.
- FastAPI authentication, domain APIs, database integration, and migrations.
- PostgreSQL schema and migrations.
- Provider adapters and ingestion jobs.
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
| 5DollarFootballAPI integration patterns | Inspect and adapt provider transport/parsing patterns if sound. | Verify current API contract, terms, quotas, provenance, and coverage. |
| AI Midas | Potential historical-statistics and additional-odds source. | Its authorization as a source does not certify bookmaker-specific timestamped closing odds or CLV suitability. Verify each field and use case independently. |
| Historical football data | Import/cache selected raw records where permitted. | Preserve provenance; validate IDs, timestamps, competition mapping, duplicates, and rights. |
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

Add new decisions with dates. Do not silently overwrite material architectural decisions; record the reason for changes.

## 11. Blockers and risks

- **Build verification pending:** the GitHub Actions workflow has been committed, but successful CI results have not yet been observed.
- **Incomplete product implementation:** current backend and Android code are minimal foundations, not a working football analysis application.
- **Provider coverage and terms:** must be verified before Stage 2 integrations are approved.
- **Historical data quality:** imports may contain missing IDs, incomplete timestamps, or inconsistent competition naming.
- **Global coverage:** quality will vary; restricted competitions must remain unpublished until evidence improves.
- **Cost/quota control:** ingestion and research must use incremental sync, caching, deduplication, and explicit request budgets.

No active external blocker has been verified at this point.

## 12. Next execution queue

1. Inspect the first GitHub Actions run and record its exact result.
2. Fix any failing backend tests, lint checks, Android SDK setup, or Gradle compilation.
3. Verify a successful clean Android debug build and backend test run.
4. Add configuration and API-contract foundations only where required for Stage 1.
5. Record CI run identifiers and close Stage 1 only when all exit criteria pass.

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
