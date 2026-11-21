# VELTRIX AI ANALYST — Project Progress Register

> Canonical execution tracker for the VELTRIX AI ANALYST project. Update this document whenever implementation status, scope, decisions, blockers, or validation evidence changes.

**Last updated:** 2026-11-21 (PR #138 shrinkage audit merged; dated ledger update staged)
**Repository:** https://github.com/Nexora-Apparel/veltrix-ai-analyst  
**Default branch:** `main`  
**Repository visibility:** Public  
**Product:** Personal-use, cloud-backed native Android football analysis and prediction application

## Latest execution checkpoint — bounded cross-provider odds qualification (2026-11-18)

- [x] The Odds API zero-credit catalogue authentication was confirmed in run [#44220418309](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44220418309): HTTP 200, 46 active soccer sport keys, one request, zero retries, `x-requests-last=0`, `x-requests-remaining=271`, `x-requests-used=229`.
- [x] User explicitly authorized use of the existing Odds API account for this project. Continue to conserve credits and obey the exact-scope internal approval; no commercial use or raw redistribution.
- [x] PR [#47](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/47) added strict offline event-to-fixture matching: exact home/away orientation, kickoff within five minutes, unique match only; alias inference, reversed orientation, drift and ambiguity fail closed.
- [x] PR [#48](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/48) added a manual cross-provider fixture catalogue qualification workflow. It makes one quota-free Odds API events request and one 5Dollar scheduled-fixture request, with no retries, pagination, DB writes or recurring schedule. A partial 5Dollar catalogue cannot qualify a market request.
- [x] PR [#49](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/49) added strict parsing/tests for a single event-specific h2h response, including event/sport identity, home-away orientation, kickoff alignment, timestamp and price validation.
- [x] PR [#51](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/51) enabled exactly one event-specific h2h request only after both catalogues are complete and exactly one unique exact fixture match exists. One region (UK), one market (h2h), no retries or pagination.
- [x] PR [#52](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/52) added parsing and recording of the actual `x-requests-last` cost; missing/invalid cost and any cost above the strict one-credit cap are explicit fail-closed outcomes.
- [x] PR #52 CI run [#44224762047](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44224762047) passed Android debug build and backend tests/Ruff. Debug APK artifact [14391932429](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44224762047).
- [ ] **Manual dispatch blocker:** run the [Cross-provider fixture catalogue qualification workflow](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/the-odds-api-5dollar-fixture-qualification.yml) for one competition. This GitHub integration session exposes read/write repository and artifact tools but no Actions workflow-dispatch operation; the workflow must be started from GitHub Actions by a repository user.
- [ ] After dispatch, inspect all manifests: both catalogue completeness flags, exact-match manifest, h2h response hash, bookmaker/selection timestamp completeness, `actual_quota_cost`, and remaining quota. Stop if actual cost exceeds one credit or any identity/completeness check fails.
- [ ] Compare The Odds API's timestamped h2h quote coverage against the 5Dollar Bet365 snapshot. A successful request is provider-access evidence only, not PIT certification. Local `retrieved_at` must be no later than the prediction cutoff; source `last_update` alone does not prove local availability.
- **No ingestion, database writes, recurring collection, odds-derived model features, CLV claims, value betting, production prediction endpoint, model promotion, public forecast publication or Android/backend prediction integration is enabled.** The retrospective v1/v2 models remain non-PIT-certified.

## Previous checkpoint — The Odds API catalogue and event discovery

## Latest execution checkpoint — The Odds API catalogue and event discovery (2026-11-18)

- [x] PR [#44](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/44) merged; manual-only catalogue workflow is on `main`.
- [x] Manual workflow run [#44220418309](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44220418309) completed successfully on merge commit `b71bfa82ae59dc52134ed2609aa7c56dd8c39cb7`.
- [x] Existing `THE_ODDS_API_KEY` secret authenticated successfully: `GET /v4/sports/` returned HTTP 200 and 46 active soccer sport keys.
- [x] Probe made exactly one request, zero retries, and reported `x-requests-last=0`, `x-requests-remaining=271`, `x-requests-used=229`. No odds credits were consumed; 271 remains the last verified balance.
- [x] Added a manual, one-sport, one-request event-discovery dry-run workflow on research branch `research/the-odds-api-zero-credit-event-discovery`. It calls only `/v4/sports/{sport}/events`, which The Odds API v4 documentation identifies as quota-free; it does not request markets, write to Neon, or activate model features.
- [x] Added strict event catalogue normalization and unit tests for future-event filtering, exact sport-key matching, duplicate IDs, required fields, timezone awareness and team identity sanity.
- [x] Event-discovery PR [#45](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/45) merged as `d483d4cd6286849c59f1601e1cdb534cacbdb023`; pre-merge CI run [#44221421575](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44221421575) passed 196 backend tests, Ruff and Android debug build.
- [x] The Odds API terms review is committed at `docs/providers/THE_ODDS_API_TERMS_REVIEW.md`; internal rights approval is exact-scoped to seven sport keys, non-commercial, and prohibits raw redistribution.
- [ ] Manually dispatch event discovery for one competition, then compare event IDs/team identities/kickoff against canonical 5Dollar fixtures. This requires one user-side workflow dispatch; it is expected to consume zero odds credits, and returned quota headers must verify this.
- **Provider qualification remains research-only.** No market requests, DB writes, recurring collection, model feature activation, CLV, value betting, production predictions or Android integration.

Detailed design: [The Odds API Event Discovery — Zero-Credit Qualification](ledger/2026-11-18-odds-api-event-discovery-design.md).

## Latest execution checkpoint — Stage 2 canonical closure (2026-11-17)

- [x] Controlled Round 38 import run [#44107179999](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44107179999) succeeded: import run 5, two of four requests used, ten fixtures inserted, zero duplicates/rejections/quarantines. Provider scope is 384 fixtures (380 FINISHED, four UNKNOWN).
- [x] Incremental materializer PR [#22](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/22) merged as `1f45c1b3547d77d3127b84a111e3611e63efeb72`; CI run [#44116261032](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44116261032) passed 122 backend tests, Ruff and Android debug build.
- [x] Production incremental materialization run [#44117463950](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44117463950), job [#134159364294](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44117463950/job/134159364294), completed with `CANONICAL_INCREMENTAL_COMMITTED`: ten fixtures created, 374 reused, zero unlinked, zero identity-review events created, zero PIT observations promoted.
- [x] Independent post-run Neon verification: 21 canonical teams, one competition, 384 canonical fixtures; 21 team links, one competition link, 384 fixture-source links; zero unlinked provider fixtures; 28 review cases / 28 review events; zero PIT features.
- [x] Provenance/uniqueness audit: all 384 fixture-source links match exact source-observation and source-sighting provenance; zero duplicate provider-fixture links; all 384 links remain `REVIEW_REQUIRED`.
- [x] All 384 canonical fixtures remain `SOURCE_ROW_ONLY`; 382 remain `IDENTITY_REVIEW_REQUIRED`, two remain `CONFLICT`. No identity merge, alias approval, reparenting or duplicate exclusion was activated.
- **Stage 2 status: COMPLETE for historical ingestion, provenance, canonical coverage and structural reconciliation.** This does not clear the 28 human-pending identity cases or PIT publication/availability timestamp requirements. No model training from PIT-ineligible data is authorized.
- Detailed evidence: [Stage 2 closure audit](ledger/2026-11-17-stage-2-closure-audit.md) and [Round 38 canonical incremental ledger](ledger/2026-11-17-round38-canonical-incremental.md).

## Earlier Stage 2 closure checkpoint — before Round 38 incremental import (2026-11-17)

- [x] Production migrations 001–009 are applied; migration 009 is independently read-verified.
- [x] Production canonical layer: 21 teams, one competition, 374 fixtures; 21 team links, one competition link, 374 fixture-source links.
- [x] Review queue: 28 cases and 28 automated recommendation events; zero active aliases and zero active duplicate exclusions. No automatic identity promotion occurred.
- [x] Historical import run 3 completed: 34/40 requests, 374 rows inserted, 370 FINISHED and four UNKNOWN.
- [x] Independent matchup audit: 20 teams, 37 appearances per team, 370 distinct directed pairings, no repeated directed pairing; 180 unordered pairs have both directions and exactly 10 directed pairings are absent.
- [x] The 10 absent directed pairings match exactly the CBF Round 38 schedule: América MG–Avaí; Atlético-GO–Cuiabá; CRB–Ceará; Criciúma–Novorizontino; Fortaleza–Vila Nova; Juventude–Botafogo-SP; Londrina–Náutico; Ponte Preta–Operário-PR; São Bernardo–Athletic; Sport–Goiás.
- [x] CBF official report confirms all 10 Round 38 results; those results are reconciliation evidence only and have not been inserted into Neon.
- [x] Four UNKNOWN rows remain scoreless duplicate/stale candidates; America MG identity collision and all 28 review cases remain human-pending.
- [x] PIT audit remains fail-closed: 374 observations, 374 sightings, zero PIT-certifiable. No pre-match feature promotion or model training.
- [x] Dedicated bounded Round 38 ingestion path merged in [PR #20](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/20), merge commit `69f91a99b162804fa6a1baa8cd35d9cdc3388488`. CI run [#44102095868](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44102095868) passed backend tests, Ruff and Android debug APK build.
- [x] Round 38 import completed in workflow run [#44107179999](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44107179999); see the latest execution checkpoint above for canonical materialization status.
- **Historical checkpoint status:** the import blocker recorded at the time is resolved; the separate canonical incremental materialization remains pending.
- Detailed evidence and exact final-round results: [Stage 2 closure audit](ledger/2026-11-17-stage-2-closure-audit.md). Incremental materializer implementation and verification gate: [Round 38 canonical incremental ledger](ledger/2026-11-17-round38-canonical-incremental.md).

## Historical checkpoint — canonical materialization and identity/coverage audit (2026-11-17)

- [x] Guarded canonical materialization workflow [#44086857898](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44086857898), job [#134051435015](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44086857898/job/134051435015), completed successfully on commit `e6ca720ca556c5cb6aea7e867075e841b0f7bf3e`; runner reported `MATERIALIZATION_COMMITTED`.
- [x] Independent read-only Neon verification confirmed 21 canonical teams, one competition, 374 canonical fixtures, 21 team links, one competition link, 374 fixture-source links, zero identity review events and zero pre-match feature observations.
- [x] All team and competition links remain `REVIEW_REQUIRED`; all fixture source links remain `REVIEW_REQUIRED`; all 374 fixtures remain `SOURCE_ROW_ONLY`. Two fixture rows remain `CONFLICT`; 372 remain `IDENTITY_REVIEW_REQUIRED`. This is deliberate fail-closed behavior, not a failed materialization.
- [x] Read-only audit identified all four `UNKNOWN` rows as duplicate/stale candidates (three exact team-ID matches and one America alias match) for already imported `FINISHED` rows. Independent CBF match records:
  - Goiás 3–1 América MG, 2026-03-22, Round 1, official match [832843](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/goias-x-america/832843); provider pair 3116209225 (FINISHED 3–1) / 2341822348 (UNKNOWN).
  - Fortaleza 3–0 Londrina, 2026-05-23, Round 10, official match [832976](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-londrina-saf/832976); provider pair 1587564237 (FINISHED 3–0) / 2336910968 (UNKNOWN).
  - Fortaleza 1–0 Botafogo SP, 2026-07-28, Round 20, official match [833076](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-botafogo/833076); provider pair 236839304 (FINISHED 1–0) / 933498248 (UNKNOWN).
  - Ceará 2–1 Londrina, 2026-08-22, Round 24, official match [833116](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/ceara-x-londrina-saf/833116); provider pair 553958702 (FINISHED 2–1) / 1988139832 (UNKNOWN).
- [x] America identity collision evidence: provider team ID `1102583842` / `America MG` appears in 37 fixture rows; ID `3808811746` / `América Mineiro` appears only in the duplicate UNKNOWN Goiás row. CBF records one official Goiás 3–1 América MG match. Strong alias evidence; do not rewrite source IDs or merge canonical placeholders without human confirmation.
- [x] CBF's 2026 schedule lists Round 37 on 6–8 November and Round 38 on 14 November. Run 3 ends 9 November and contains 370 FINISHED rows, numerically equal to 37 rounds × 10 fixtures. This is not yet fixture-by-fixture proof of completeness; the 370 finished rows still need reconciliation against the official 370 scheduled pairings. The final round of 10 matches is outside run 3's collection window.
- [x] PIT audit: 374 fixture observations and 374 sightings; zero observations and zero sightings PIT-certifiable. No pre-match feature promotion is permitted.
- [x] PR [#18](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/18) merged at `0d069138aad8ce4e25a2339cce3056f00431b9f0`. CI [#44092601005](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44092601005) passed backend tests, Ruff, Android debug build and APK upload. Migration 009 adds immutable evidence-backed review cases, automated recommendation events, source-provenance audit views, and seeded cases for 20 team identities, the America alias, competition identity, four duplicate fixtures, season coverage and PIT timestamp gap. All require explicit human confirmation; no canonical/source row is rewritten by the migration.
- [ ] Migration 009 has been successfully prepared and tested on an isolated Neon branch copied from production. Test results: 28 cases, 28 automated recommendations, 21/1/374 source provenance verified, four duplicate cases, zero activated aliases/dedup exclusions, and unchanged canonical/PIT row counts. The controlled production migration workflow must still be manually dispatched after explicit user approval, then independently verified. No production migration is applied yet.
- **Remaining hard gates:** human approval of identity/duplicate cases; exact 370-fixture official schedule reconciliation; source publication/availability timestamps and rights-qualified PIT evidence; final 10 Round 38 results are outside import run 3.
- **No model training, feature engineering from these records, prediction publication, or Android/backend prediction integration is authorized.**

## Historical checkpoint — before first canonical materialization

- Migration 008 was successfully applied and verified against Neon database `veltrix_ai_analyst` through controlled workflow [#44078914169](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44078914169), job `134024119643`. Exact SHA-256: `bbd3276a85d7e6d9c8293379b173b15753fb96c3f2877c6488229f5a011c8130`.
- Live read-only database checks confirmed migration records 006, 007 and 008, the corrected `enforce_canonical_link_provenance()` function, and unique provider-local team and competition identity-link indexes.
- Canonical materializer PR [#15](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/15) remains merged at `f7a73046be1b3ab0459815c636adfa202ba41e9f`.
- Read-only production preview PR [#16](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/16) merged at `7cf34b5f0541667b2ebcd2ddaabff13cfc738a6c`. Its validated head was `d1ebe60997e2023681de3b8f826ebd1f39b84971`.
- CI run [#44080635104](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44080635104) passed Android debug build, backend tests and Ruff lint including the preview runner.
- Patch review confirmed the preview workflow is manual-only, defaults to NO, requires `PREVIEW_BRAZIL_SERIE_B_RUN_3`, targets the dedicated GitHub Actions environment/secret, checks the exact database name, and enforces PostgreSQL read-only mode at both connection and transaction levels. The runner calls only `build_brazil_serie_b_materialization_plan`; it never calls the writer or passes `execute=True`.
- Production read-only preview [#44085484843](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44085484843), job `134046688821`, completed successfully on main commit `ab0dc0a50af6cbde66431ad7e872c2e4e8b8f41a`. Planner reported `ready=true`, zero blockers, 1 competition, 21 teams, 374 fixtures, 370 finished, four unknown, 2 conflict fixture IDs (`2341822348`, `3116209225`), and 396 non-PIT observations. All 374 fixture, 21 team and one competition provenance counts reconciled.
- Independent post-preview read-only Neon query confirmed all seven canonical tables still contain zero rows. No canonical materialization, identity review event, PIT promotion, provider HTTP request, model training or prediction publication has occurred.
- Source scope remains 5DollarFootballAPI Brazil Serie B competition `522514093`, import run 3: 374 fixtures, 21 teams and one competition. 370 fixtures are FINISHED with scores; four remain UNKNOWN and scoreless. The America MG / América Mineiro near-simultaneous fixture pair remains unresolved and must remain conflicted.
- The 396 scoped source observations remain non-PIT-certifiable. A successful canonical preview or later source-row materialization does not grant PIT eligibility or authorize model training.
- Guarded first-run materialization PR [#17](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/17) merged at `60e24970c2dd847773d685ba903238e99c5c3da8`; CI [#44086260165](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44086260165) passed backend tests, Ruff, Android debug build and APK upload.
- The new manual-only workflow defaults to NO and requires `MATERIALIZE_BRAZIL_SERIE_B_RUN_3`. Its runner rechecks the exact plan and empty target inside one SERIALIZABLE transaction, applies the writer, and verifies exact row counts before commit. Any mismatch rolls back.
- **Production write not yet executed.** The workflow is available at [Materialize canonical entities](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/materialize-canonical-entities.yml). Manual dispatch requires branch `main` and `confirm_materialization=MATERIALIZE_BRAZIL_SERIE_B_RUN_3`; this session cannot dispatch GitHub workflows. Do not execute without explicit user decision.
- Last independent Neon check after the preview confirmed all seven canonical tables were empty. PR #17 merge itself did not modify production data.
- Supplemental evidence is recorded in `docs/ledger/2026-11-17-canonical-materialization-review.md`, `docs/ledger/2026-11-17-read-only-preview-pr16.md`, and `docs/ledger/2026-11-17-guarded-canonical-materialization-pr17.md`.

## Current verified position

- **Current stage:** Canonical materialization; next gate is the explicit, manually dispatched guarded first production write.
- **Merged:** canonical schema migrations 007/008, read-only-by-default canonical materializer, read-only preview workflow, and guarded first-run materialization workflow.
- **Pending:** explicit manual dispatch of the guarded first-run materialization workflow, followed by JSON report review and independent Neon count verification. The workflow is production-write capable and has not been executed.
- **Not built:** point-in-time feature pipeline, model training/calibration, prediction API, production deployment.
- **No prediction model has been trained or certified.**
- **Project isolation:** no VELTRIX FOOTBALL 2.0 prediction logic, weights, priors, calibration, historical data or decision rules are reused.

## Historical import attempt #1 — BLOCKED BEFORE PROVIDER HTTP

- Workflow run [#43954509888](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43954509888), job [#133605398471](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43954509888/job/133605398471), was manually dispatched on 2026-11-16 and failed in `PostgresIngestionStore.sync_source_approval()` with `SOURCE_APPROVAL_ID_ALREADY_EXISTS_WITH_DIFFERENT_EVIDENCE`.
- Root cause: `scope_values`, `data_types`, and `permitted_uses` are semantic sets in `SourceApproval`, but are stored as JSONB arrays. The comparison sorted the in-memory sets but compared them to persisted arrays in their original order. The registered approval values were semantically identical; ordering alone caused the false conflict.
- Read-only Neon verification confirmed the registered approval's provider, source, scope, seven competition IDs, data types, approved status, terms evidence hash, permitted uses, non-commercial restriction and attribution/raw-redistribution flags match the code grant.
- Failure occurred while creating the import run, before the fixture request loop. Read-only counters after failure: 0 fixture request events, 0 fixture response records, 0 imported provider fixtures. The two existing import runs, 80 request reservations and 68 checkpoints are the prior DB-only dry-run/rehearsal records; they are not provider HTTP calls.
- PR [#10](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/10) canonicalizes the three stored JSONB arrays before comparing them and adds a PostgreSQL regression test that reverses all three arrays. It does not modify or broaden the rights grant.
- At the time of this incident record, collection was paused pending CI, merge and read-only preflight. Those gates have since passed on 2026-11-16; see the latest verification section below. The import still requires a manual `workflow_dispatch` launch.

## Stage 2 — Verified evidence

### Repository and CI
- PR #1 merged (`c219b4d`); CI run #43858717326 passed 44 backend tests, Ruff lint, Android debug build and APK artifact upload.
- PR #2 merged (`f3bec93`); CI run #43860443460 passed 52 backend tests, Ruff lint, Android debug build and APK artifact upload.
- PostgreSQL migrations are tested against ephemeral PostgreSQL. Remote migration requires explicit opt-in and an expected database name; legacy VELTRIX Football DB names are blocked.

### AI Midas Brazil Serie B snapshot
- GitHub Actions run [#43882958891](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43882958891) completed successfully.
- Pinned CSV: 192,284 bytes; SHA-256 `55b0c00629abd2d4ff3c31659ada950b67ffc2752609284b32c15c99f71152ab`; Git blob SHA-1 `b6bdb94c053d2149e6232fb100e1f158e46e4533`.
- 738 team-match rows, 369 matches, 20 teams; 2026-03-21 through 2026-11-08.
- One inconsistent match (Náutico 0–3 CRB, 2026-11-07; two inconsistent team rows) was quarantined; 368 matches remain descriptive candidates.
- Raw CSV remained in runner temporary storage; only a sanitized manifest artifact was retained.
- Non-commercial only; no verified source publication timestamp; descriptive-only, not PIT-certified, not eligible as pre-match model features, and not CLV-qualified.

### 5Dollar Community account preflight
- Run [#43884649616](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43884649616) succeeded.
- Community plan; reported 300 requests/hour and 20/minute burst; Brazil Serie B visible as competition ID `522514093`.
- This proved account and competition catalogue access only.

### 5Dollar Brazil Serie B fixture endpoint probe — EXECUTED
- Run [#43916841159](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43916841159), workflow `5dollar-fixture-probe.yml`, commit `c6be115cf278c3466ee1d6c30b05efc80e2c3359`, completed successfully on 2026-11-16.
- Job: “One-request fixture endpoint probe”; all steps completed successfully.
- Actual endpoint: `GET /v1/leagues/522514093/fixtures`.
- Scope: 2026-11-07T00:00:00Z inclusive to 2026-11-09T00:00:00Z exclusive; page 1; page size 100.
- Manifest confirms HTTP 200, 8 rows, pagination count 8, `has_more=false`; one request, zero retries, zero pagination follow-ups.
- Response size 3,872 bytes; response SHA-256 `76009f299a3d4a42e9df54d8d9cf6682a43b7e3f36c12713a7cc940d41fc88d8`.
- Returned fields: `cards`, `corners`, `goals`, `id`, `kickoff_ts`, `kickoff_utc`, `league`, `status`, `status_code`, `status_reason`, `teams`.
- First fixture sample: ID 3728617699; kickoff `2026-11-08T22:15:00+00:00`; status `finished`. Timestamp evidence currently establishes kickoff/event time fields only, not source publication/availability time.
- Sanitized artifact `5dollar-brazil-serie-b-fixture-probe`, artifact ID 14250910940, 704 bytes, 7-day retention. Raw response and credential were not uploaded or printed.
- This qualifies endpoint access and the sampled response schema for this exact two-day window only. It does not establish season completeness, historical coverage, result-field completeness across the competition, source publication timestamps, odds availability, PIT eligibility or model eligibility.

## Immediate next execution queue

1. Inspect and document fixture/result field semantics and the adapter's compatibility with the observed schema. Add bounded contract tests using the captured sanitized manifest/sample shape; do not expand provider requests to solve schema questions.
2. Design a date-windowed, resumable historical collection budget using the measured pagination behaviour. Keep an explicit hard request ceiling and stop conditions.
3. Provision a separate private PostgreSQL database only after the exact target and credentials are configured; never reuse the legacy database.
4. Test the end-to-end ingestion orchestrator against ephemeral PostgreSQL before any historical import.
5. After measured source coverage and rights/timestamp review, define the Stage 3 football-intelligence feature pipeline.
6. Implement statistical models only after point-in-time data and chronological evaluation controls are established.

## Standing constraints

- No bulk history pull, odds expansion, database provisioning, import, model training or production deployment has been performed by the probe.
- Do not treat kickoff timestamps as source publication timestamps.
- Do not infer whole-season coverage from an 8-row two-day sample.
- Keep API keys, raw provider payloads and private data out of the public repository and CI artifacts.
- Preserve the independent model rebuild boundary from VELTRIX FOOTBALL 2.0.


### 5Dollar adapter contract audit — 2026-11-16
- [x] Compared the bounded fixture probe route and query parameters with `backend/app/providers/five_dollar.py`; route and request parameter names match.
- [x] Confirmed the adapter normalizes all sampled top-level fixture field families: IDs, league, teams, kickoff, status, goals, corners and cards.
- [x] Added offline tests in `backend/tests/test_five_dollar_observed_contract.py` for the observed eight-row pagination envelope, exact route/query, mapped field families and `kickoff_ts` fallback.
- [x] No additional provider calls were made; test data is synthetic and does not contain the raw provider payload.
- [ ] CI run #43917944552 is pending/in progress at the time of this update; do not treat the test addition as validated until backend tests, Ruff and Android build finish successfully.
- [ ] Next: complete CI verification, then design a request-budgeted resumable historical collection plan. Do not start a bulk pull.


### 5Dollar collection budget design — 2026-11-16
- [x] Added `docs/5DOLLAR_BRAZIL_SERIE_B_HISTORICAL_COLLECTION_PLAN.md` (VAA-INGEST-PLAN-001 v1.0).
- [x] Plan is limited to Brazil Serie B provider ID `522514093`, candidate interval 2026-03-21 to 2026-11-09 UTC, fixture/results only.
- [x] Set a hard 40-fixture-request ceiling, seven-day non-overlapping windows, page size 100, no retries, and explicit stop/checkpoint rules.
- [x] Documented source-rights, attribution, four-day result-availability proxy and non-PIT restrictions.
- [ ] Plan is design-only: no collection requests, database provisioning, imports or model operations have been performed under it.
- [x] CI run #43917944552 completed successfully: backend tests, Ruff lint, Android debug build and APK artifact upload all passed.


### Deterministic collection-window planner — 2026-11-16
- [x] Added `backend/app/providers/collection_plan.py` with timezone-aware UTC normalization and contiguous, non-overlapping half-open date windows.
- [x] Added `backend/tests/test_collection_plan.py` for the 34-window Brazil Serie B candidate interval, UTC offset normalization, clipped final window, and invalid-input rejection.
- [ ] CI run #43918522018 is running; the earlier intermediate run for the first planner commit was cancelled by the immediately following test-file commit. The current run is the validation target.
- [ ] This planner is a pure offline utility. It does not call the provider, persist data, reserve API quota, or authorize collection.



### Persistent request budget, checkpoint recovery and controlled dry-run — 2026-11-16
- [x] Added migration `003_import_request_reservations.sql` with a durable reservation ledger and a PostgreSQL-level `request_budget <= 40` constraint.
- [x] Added `PostgresRequestBudget`: serializes reservations by locking the import-run row, commits each reservation before network use, rejects request 41, and prevents duplicate idempotency keys from authorizing a second HTTP request. A repeated reservation returns `created=false`; changed request data under the same key raises a conflict.
- [x] Added deterministic `load_checkpoints` recovery to `PostgresIngestionStore`; checkpoint tests verify a fresh store can recover completed window state after interruption.
- [x] Added PostgreSQL integration coverage for concurrent distinct reservations, concurrent duplicate keys, idempotency conflicts, paused-run refusal, and a 41-request rejection.
- [x] Added provider stop-condition tests for HTTP 401/403/500, 429 without retry, moved league IDs, and malformed score/schema data.
- [x] Controlled dry-run in ephemeral PostgreSQL simulated the 34 planned windows: 34 first-page reservations plus six second-page reservations; all 34 checkpoints were recovered; request 41 was rejected. No provider HTTP requests were made.
- [x] Added a run-bound callback from `PostgresRequestBudget` into `FiveDollarFootballProvider.fetch_fixtures`; historical collection can require a reservation before every page request, and duplicate reservations block the HTTP call.
- [x] Added a PostgreSQL-backed provider boundary integration test: the first reservation permits one mocked HTTP request; replay of the same page is rejected before a second HTTP request.
- [x] CI run [#43922283499](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43922283499) passed: 76 backend tests, Ruff lint, Android debug build and APK artifact upload.
- [ ] Independent Neon production database is not provisioned. The only connected Neon organization is Vercel-managed; direct Neon project creation is restricted. The Neon Marketplace integration is installed, but resource provisioning requires the Vercel Marketplace/CLI flow. Do not reuse the legacy `VELTRIXFOOTBALL` project.
- [ ] After the separate Neon resource exists: configure its connection string as a secret, apply checksum-verified migrations with explicit database-name/remote opt-in, verify `current_database() = 'veltrix_ai_analyst'`, then run the dry-run against that database.- [ ] Live historical collection remains blocked; no historical provider requests or DB writes have been made.



### Provider HTTP reservation boundary — 2026-11-16
- [x] `FiveDollarFootballProvider.fetch_fixtures` supports a run-bound request-reserver callback.
- [x] Historical collection can set `require_request_reservation=True`; missing callback fails before network access.
- [x] The callback runs before each page request. A duplicate reservation (`created=false`) blocks the HTTP request.
- [x] `PostgresRequestBudget.callback_for_run` binds the persistent reservation service to one import run.
- [x] PostgreSQL integration test verifies one durable reservation authorizes one mocked HTTP request and a replay is stopped before HTTP.
- [x] Final CI run [#43922283499](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43922283499) passed: 76 backend tests, Ruff, Android debug build and APK artifact upload.
- [ ] No production Neon resource exists yet. The Vercel-managed Neon organization rejects direct project creation; provisioning must be performed through the installed Vercel Marketplace Neon integration.
- [ ] No real historical collection request has been made; keep collection blocked until the separate DB is provisioned, migrated, identity-verified and dry-run tested.


### Dedicated Neon database and dry-run — 2026-11-16
- [x] Vercel CLI authorization and project linking verified.
- [x] Dedicated Neon resource `young-wind-27772160`; database `veltrix_ai_analyst`; PostgreSQL 18.7. Exact database identity verified.
- [x] Migrations 001–003 applied through Neon SQL transactions; checksums recorded and read back from `public.schema_migrations`. See `docs/ledger/2026-11-16-neon-migrations-and-dry-run.md`.
- [x] Existing reviewed 5Dollar Community approval registered for the documented competition and data scope.
- [x] Corrected Neon-backed dry-run run ID 2: 34 contiguous checkpoints, 40 simulated reservations, 34 recoverable checkpoints, request 41 rejected, provider-compatible idempotency key format, zero provider HTTP calls and zero fixture rows.
- [x] Initial rehearsal run ID 1 marked FAILED after detecting millisecond formatting in idempotency keys; no provider calls were made. Corrected run ID 2 is PAUSED with `DRY_RUN_ONLY_NO_PROVIDER_HTTP`.
- [ ] Python migration runner was not executed because Vercel CLI environment pull redacted the sensitive `DATABASE_URL`; migrations were applied directly through Neon SQL and checksums verified.
- [ ] Live historical collection remains gated on a tested resumable importer/orchestrator and secure configuration of the dedicated DB connection for the GitHub Actions runner. Vercel integration-generated URL variables currently target `neondb`, not `veltrix_ai_analyst`.
- [x] No historical 5Dollar API calls, odds calls, fixture imports, model training or prediction publication.


### Historical importer — 2026-11-16
- [x] PR #3 merged: resumable Brazil Serie B importer, response provenance, fixture persistence, 34 checkpoints, page resume, 40-request cap and 12-second request spacing.
- [x] Manual-only workflow requires explicit collection confirmation and an optional paused run ID.
- [x] CI #43941999882 passed 80 backend tests, Ruff, Android debug build and APK artifact upload. Tests use mocked HTTP; no 5Dollar calls were made.
- [ ] Live import remains locked until `VELTRIX_AI_ANALYST_DATABASE_URL` is securely configured as a GitHub Actions environment secret.
- [ ] Add raw-response capture and quarantine for non-success or malformed responses before live collection. Existing importer stops safely and does not retry a reserved request.
- [x] No historical 5Dollar requests, odds calls, fixture imports, model training or prediction publication occurred.


### Failed-page capture and quarantine — 2026-11-16
- [x] PR #4 merged at `cabdf8c2cfd831ad67cf9979ddb783b77906b5a4`: raw HTTP responses captured before validation; request events persisted; failed pages quarantined with linked response ID/checksum/status; automatic replay blocked for unresolved quarantines.
- [x] CI #43944083287 passed 82 backend tests, Ruff, Android debug build and APK artifact upload. Malformed JSON test verifies raw body retention and quarantine.
- [x] Migration 004 applied to Neon database `veltrix_ai_analyst`; SHA-256 `567fc4c0f85e0b228591bda0888b76a82b92cb799b129197d8e4aae3404997cf`; five columns and unique request-key constraint verified.
- [ ] Live collection remains locked until `VELTRIX_AI_ANALYST_DATABASE_URL` is securely configured as a GitHub Actions secret.
- [x] No 5Dollar historical requests, odds calls, fixture imports, model training or prediction publication occurred.


---

## 14. Latest authoritative checkpoint — 2026-11-16

This section supersedes older queue entries above where they describe the importer, quarantine, Neon provisioning, or migration status as incomplete.

### Implemented and merged
- PR #1 and PR #2: provenance-first PostgreSQL schema and runtime ingestion store.
- PR #3: fixed-scope, resumable Brazil Serie B historical importer and manual-only workflow.
- PR #4: raw HTTP response capture and failed-page quarantine; unresolved quarantines block automatic resume.
- Migration 004 applied to the dedicated Neon database; SHA-256 `567fc4c0f85e0b228591bda0888b76a82b92cb799b129197d8e4aae3404997cf`.
- Importer implementation: `backend/app/providers/historical_import.py`.
- CLI: `scripts/collect_brazil_serie_b_history.py`.
- Workflow: `.github/workflows/historical-brazil-serie-b.yml`.
- CI #43944083287 passed 82 backend tests, Ruff, Android debug build and APK artifact upload. The importer integration tests use mocked HTTP; this is not a live provider collection.

### Database state
- Dedicated Neon resource: `young-wind-27772160`.
- Database identity: `veltrix_ai_analyst`, PostgreSQL 18.7.
- Migrations 001–004 are applied and checksum-verified.
- The Vercel CLI's sensitive environment pull redacted `DATABASE_URL`; the Python migration runner was not executed. Migrations were applied through the authenticated Neon SQL connection and verified in the migration ledger.
- Neon-backed rehearsal run 2 is PAUSED with `DRY_RUN_ONLY_NO_PROVIDER_HTTP`: 34 contiguous checkpoints, 40 simulated reservations, all checkpoints recovered, request 41 rejected, zero fixture rows and zero 5Dollar HTTP requests. This rehearsal consumed no provider quota.

### Current blocker — GitHub Actions database secret
- Required GitHub Actions environment: `veltrix-historical-import`.
- Required environment secret: `VELTRIX_AI_ANALYST_DATABASE_URL`.
- It must contain the dedicated `veltrix_ai_analyst` database URI, not the integration's `neondb` URI.
- GitHub connector does not expose repository/environment secret write APIs in this session. Do not attempt to transmit the credential through chat, source code, workflow inputs, logs, or artifacts.
- Secure setup instructions: `docs/GITHUB_ACTIONS_DATABASE_SECRET_SETUP.md`.

### Hard safety state
- Live historical import: **LOCKED**.
- Historical 5Dollar requests under this collection plan: **0**.
- Imported fixture rows: **0**.
- Odds requests: **0**.
- Model training/prediction publication: **not started**.
- Request budget remains **40 maximum**, no automatic retries, 12-second minimum request spacing.
- No use of the VELTRIX FOOTBALL 2.0 database, prediction logic, priors, or model artefacts.

### Next execution sequence
1. Configure the dedicated database URI as the GitHub environment secret.
2. Add/run a zero-provider-request preflight that checks database identity, migrations 001–004, approval scope and quarantine state without creating fixture rows.
3. Verify the secret-backed runner can connect to the exact dedicated database; output sanitized checks only.
4. Review the preflight and collection envelope before any live workflow dispatch.
5. If a provider request fails, preserve the raw response, quarantine it, pause the run and reconcile manually. Never retry a reserved request or exceed 40 calls.

### Documentation discipline
Every subsequent implementation, migration, CI result, provider call, import count, blocker, or scope decision must be recorded in this register and the relevant dated ledger. Never update status to PASSED based only on code inspection or a mocked test.


### Post-import quality gate — 2026-11-16
- [x] PR #5 merged at `c477516c804b0de4a8b825d29ded13fd5ea22f22`: read-only validator checks exact DB/source/date scope, 34 checkpoints, request budget and canonical hashes, raw response linkage/checksums, rights approval, fixture integrity and non-PIT provenance.
- [x] Manual workflow runs the quality validator automatically after successful import completion.
- [x] Operator instructions added: `docs/HISTORICAL_IMPORT_OPERATOR_RUNBOOK.md`.
- [x] CI #43946317661 passed 82 backend tests, Ruff, Android debug build and APK artifact upload.
- [ ] Live historical collection remains locked until GitHub Actions environment secret `VELTRIX_AI_ANALYST_DATABASE_URL` is configured with the dedicated `veltrix_ai_analyst` URI.
- [x] No historical 5Dollar API calls, odds calls, fixture imports, model training or prediction publication occurred.


### Read-only collection preflight — correction and secret setup confirmation (2026-11-16)
- [x] User confirmed the GitHub environment secret `VELTRIX_AI_ANALYST_DATABASE_URL` was saved in `veltrix-historical-import`. Its value remains private and is not yet validated by GitHub Actions.
- [x] Read-only Neon inspection identified the actual registered approval: `approval-5dollar-community-fixtures-2026-11-12`. The earlier PR implementation referenced a nonexistent approval ID.
- [x] Verified that approval belongs to `5DollarFootballAPI` / `5dollarfootballapi`, includes competition `522514093`, and permits fixtures/results plus competition/team catalogue data; it is non-commercial, requires attribution and disallows raw redistribution.
- [x] Corrected preflight approval binding and added a regression test.
- [x] Reconfirmed database identity `veltrix_ai_analyst`, PostgreSQL 18.7, migration checksums 001–004, zero unresolved 5Dollar quarantine rows and zero PLANNED/RUNNING 5Dollar import runs.
- [x] PR #7 merged after CI run #43949016507 passed backend tests, Ruff lint and Android debug APK build/upload. Squash merge: `34f3e27dbdf9c3ddd17e9ab4fe0f92589ff00e32`.
- [ ] Run the read-only preflight from the Actions page to verify the saved secret and runner connectivity.
- [x] No provider requests, reservation writes, fixture writes, odds calls or model operations were performed during this correction.
- [x] Historical collection remains **LOCKED**.


---

## 15. Authoritative read-only preflight result — 2026-11-16

The secret-backed GitHub Actions preflight has now completed successfully. This section supersedes the older statements above that describe runner secret validation or read-only preflight execution as pending.

- [x] Run [#43949967262](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43949967262) completed with conclusion `success`; job [#133589528998](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43949967262/job/133589528998).
- [x] Runner connected using GitHub environment secret `VELTRIX_AI_ANALYST_DATABASE_URL` and verified exact database identity `veltrix_ai_analyst` (PostgreSQL 18.7).
- [x] Project schema and migrations 001–004/checksums passed.
- [x] Registered 5Dollar approval/scope passed.
- [x] Unresolved quarantines: 0; active import runs: 0.
- [x] Side effects: provider HTTP requests 0; database writes 0; fixture rows written 0.
- [x] The Actions secret is validated; its value remains private and is not recorded.
- **Gate status:** read-only infrastructure preflight PASSED.
- **Live historical collection status: LOCKED.** The preflight is not an import authorization. A separate explicit user go-ahead is required before dispatching the historical collection workflow.
- On any later authorized collection, enforce the existing Brazil Serie B-only scope, fixtures/results only, 40-request hard ceiling, durable pre-request reservations, no retries, 12-second minimum spacing, and quarantine/pause on failures. No odds calls or model training are authorized by this preflight.

Detailed evidence: `docs/ledger/2026-11-16-read-only-preflight-passed.md`.


---

## 16. Import approval identity audit — 2026-11-16

A pre-collection code audit found that `backend/app/providers/historical_import.py` derived a second approval ID (`approval-5dollar-ai-analyst-historical-2026-11-16`) even though the database preflight had verified the existing registered grant `approval-5dollar-community-fixtures-2026-11-12`. The scope and rights fields were copied from the same reviewed Community approval, but maintaining two IDs weakened the approval chain and made the code diverge from the preflight's canonical record.

- [x] Identified the mismatch before any historical import request was made.
- [x] Correction merged via PR [#8](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/8), merge commit `71eedf3abeedcd0312d7f7038b5e9541b7af5484`: importer now uses the canonical `FIVEDOLLAR_COMMUNITY_APPROVAL` object directly; no derived approval ID.
- [x] Added regression test asserting exact approval ID, provider, source, competition scope and fixtures/results data type.
- [x] Updated collection plan to prohibit derived duplicate approval IDs.
- [x] CI #43952346445 passed backend tests, Ruff lint, Android debug build and APK artifact upload.
- [x] Read-only Neon query confirmed the canonical registered approval row matches the complete source approval definition used by the importer.
- [x] No provider HTTP calls or database writes were made during this audit/correction.
- **Live historical collection remains LOCKED** pending separate explicit user authorization.


---

## 17. Point-in-time feature eligibility policy — 2026-11-16

- [x] Drafted `docs/FEATURE_ELIGIBILITY_AND_POINT_IN_TIME_POLICY.md` before any model or feature pipeline is built.
- [x] Explicitly separates valid post-match target labels from pre-match feature eligibility.
- [x] Marks 5Dollar post-match statistics and the four-day availability proxy as non-PIT-certified.
- [x] Marks AI Midas historical CSV as descriptive-only until independent publication/availability evidence is established.
- [x] Defines required event/publication/first-observed/available/retrieved timestamps, source rights linkage, feature registry, cutoff checks, chronological splits, leakage controls and training acceptance gate.
- [x] PR [#9](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/9) merged to `main` at `9e72b4a4bf6b6e03a642237c9fe3716ee837d80c` (documentation-only; no CI workflow was triggered for this docs-only change).
- No provider requests, database writes, fixture imports, odds calls or model training were performed for this policy.


## Latest verification — 2026-11-16 — PR #10 merged; import ready for dispatch

### CI and merge
- CI run [#43956828039](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43956828039), head `266182017ffced5b4bec657a26d33f554ad2ad84`, completed successfully.
- Android debug build and APK artifact upload passed.
- Backend test suite passed; Ruff lint passed.
- PR [#10](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/10) merged by squash at 2026-11-16T21:09:10Z. Merge commit: `6e37dbf7bae782e7b75a1594b69cfa8aab80a422`.

### Read-only Neon preflight
- Dedicated database `veltrix_ai_analyst`, PostgreSQL 18.7, confirmed.
- Migrations 001–004 are present in `public.schema_migrations` with checksums matching the repository migration manifests:
  - 001 `11516fc36e78cca9d0a47f677e2ab451fc1beb6b899d74f9f007b979c98ebf07`
  - 002 `a5389d81f7816837c0dfedd35784f8834c4484c13a946ea166dd6d55615c4285`
  - 003 `fa841cf34fe836f3d7d7251edd36e4d5e619d185f6adf4585ac851ebcdc0560e`
  - 004 `567fc4c0f85e0b228591bda0888b76a82b92cb799b129197d8e4aae3404997cf`
- Approval `approval-5dollar-community-fixtures-2026-11-12` remains APPROVED for 5DollarFootballAPI. Competition `522514093` is included. Data types remain fixtures/results and competition/team catalogues. Permitted uses include historical import and internal analysis/model work; commercial use is false, attribution is required, and raw redistribution is prohibited.
- Read-only counters at preflight: provider request events 0; provider responses 0; provider fixtures 0; quarantine records 0; active import runs 0; existing reservations 80; checkpoints 68. The 80 reservations and 68 checkpoints belong to prior DB-only dry-run/rehearsal records and are not provider requests.

### Historical import dispatch gate
- The original user-authorized collection scope remains Brazil Serie B competition `522514093`, interval `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`, 34 contiguous weekly windows, fixtures/results only, maximum 40 provider fixture requests, no retries, maximum 5 requests/minute, at least 12 seconds between requests.
- Workflow: [Controlled Brazil Serie B Historical Import](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/historical-brazil-serie-b.yml).
- Workflow requires a manual `workflow_dispatch` input `confirm_collection=COLLECT_BRAZIL_SERIE_B`; optional `resume_run_id` should remain blank because no live import run has been created.
- The connected GitHub toolset exposes workflow reads and reruns but no workflow-dispatch action. Therefore the manual dispatch must be submitted through the workflow page; no provider HTTP request has been initiated in this session.
- After dispatch, verify actual request reservations and workflow logs; then run `scripts/validate_brazil_serie_b_import.py` for the resulting run. Any validation failure blocks model training. No odds collection or model training is authorized by this import step.


---

## 2026-11-16 — Live historical import interrupted; partial progress verified

### GitHub Actions evidence
- Workflow run [#43957601456](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43957601456), job [#133616186995](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43957601456/job/133616186995), was manually dispatched on `main` at 2026-11-16T21:11:59Z.
- Run conclusion: `cancelled`; job import step conclusion: `cancelled`; automatic validation step: `skipped`.
- Logs show setup and dependency installation succeeded. The bounded importer process ran until GitHub reported `The operation was canceled` at 2026-11-16T21:32:16Z. No Python traceback, HTTP error or provider schema error was emitted before termination.
- Cancellation cause/initiator is not established by the available job log; do not attribute it to the user or GitHub timeout without further evidence.

### Read-only Neon recovery inspection
- Target verified: Neon project/resource `young-wind-27772160`, database `veltrix_ai_analyst`.
- Live import run ID: `3`; database status remains `RUNNING` because the runner was terminated before normal importer finalization.
- Scope remains 5DollarFootballAPI Brazil Serie B competition `522514093`, interval `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`, 34 weekly windows, request budget 40.
- 23 of 34 checkpoints are `COMPLETED`; their totals are 247 records seen, 247 inserted, 0 duplicate, 0 rejected, 0 quarantined, and 23 checkpointed requests.
- The next checkpoint, `[2026-08-29T00:00:00Z, 2026-09-05T00:00:00Z)`, remains `RUNNING`; 10 later windows remain `PENDING`.
- The reservation ledger contains 24 reservations for run 3; run counter reports 24 requests used. Provider request and response ledgers each contain 24 entries for this run's execution period.
- The 24th request returned HTTP 200 and its raw response was persisted (response ID 24; SHA-256 `7a47acbe19ace32b0965d55a4246ff1ba87a8efad182d70d65502120a042fbfa`). Its window checkpoint was not confirmed completed before cancellation.
- Across the dedicated provider fixture table, 247 rows exist for this provider/source/competition; earliest kickoff 2026-03-21T20:00:00Z and latest 2026-08-28T23:30:00Z.
- Quarantine table count remains 0.
- Inspection queries were read-only. No database mutation, retry, or second provider request was made during recovery inspection.

### Recovery decision
- Do not start a new import run and do not restart from the beginning.
- Resume the existing import run ID `3` only, after confirming the importer safely reconciles the reserved/HTTP-200 but uncheckpointed request for the Aug 29–Sep 5 window. The existing reservation must not authorize a duplicate HTTP request.
- Workflow input on the next manual dispatch: `confirm_collection=COLLECT_BRAZIL_SERIE_B`; `resume_run_id=3`.
- The automatic post-import validator must complete successfully before this dataset can be accepted. No odds collection, model training, calibration or prediction publication is authorized by this partial import.
- Import remains **INCOMPLETE / NOT VALIDATED**.


### Recovery code audit — run 3 must not be resumed until captured-response replay is implemented (2026-11-16)
- [x] Inspected `backend/app/providers/historical_import.py` and `backend/app/providers/five_dollar.py` after confirming the 24th request has a persisted HTTP 200 response but an incomplete checkpoint.
- [x] Confirmed resume currently starts a non-completed checkpoint from `cursor_value` (page 1 for this window) and calls the provider adapter again.
- [x] The persistent reservation callback correctly refuses to repeat the already-reserved request. However, the current resume path does not replay the already-captured raw response into `FixturePagePersister`; it raises the duplicate-reservation error instead.
- [x] The exception path can then quarantine the page and mark the checkpoint FAILED. Therefore dispatching run 3 with `resume_run_id=3` before a recovery fix would turn a safely captured HTTP 200 page into a manual quarantine and would not complete the import.
- [ ] Implement a deterministic captured-response replay path keyed by the exact run/window/page reservation and linked response record. Validate response status, request parameters, checksum, JSON envelope, competition/window scope and pagination before persisting fixtures/checkpoint.
- [ ] Add regression tests proving a captured HTTP 200 page is replayed without provider HTTP, the reservation is not repeated, and malformed/missing/mismatched captured responses fail closed into quarantine.
- [ ] Re-run CI, then resume only run ID 3. Do not create a new import run or repeat the reserved request.
- **Current state:** 23/34 windows complete; 247 fixtures inserted; 24/40 requests used; one captured response awaits checkpoint reconciliation; 10 windows pending; import incomplete and not validated.


### Captured-response replay implementation pass — 2026-11-16
- [x] Added an initial replay path in `backend/app/providers/historical_import.py` in commit `200ec0e7c6816926264c8a2fbddfc45d6ea29028`.
- [x] The path validates the expected request envelope, HTTP 200 linkage, raw-body SHA-256, JSON success/data/pagination structure and fixture normalization, then uses the existing transactional page persister.
- [x] Pagination continues at the next page only when the replayed page reports `has_more=true`; the captured page itself is not fetched again.
- [ ] **Not release-ready:** response evidence is currently correlated through request-event endpoint/params/time rather than a first-class foreign-key link from the durable reservation. Add reservation-to-response identity and a safe migration/backfill for run 3 before allowing resume.
- [ ] Add database-backed regression tests for exact replay, no HTTP on replay, atomic checkpoint/fixture writes, ambiguous/missing/hash-mismatched evidence, and pagination.
- [ ] Run full CI (backend tests, Ruff, Android debug build); inspect results and fix all failures.
- **Safety state:** run 3 remains paused; no new provider calls, no new import run, no model training, and no publication. The initial code commit is not evidence that recovery is validated.


---

## 2026-11-16 — Run 3 captured-response recovery fix merged

- [x] PR [#11](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/11) merged by squash; merge commit `ff8e59c52d9ff5c189570a9a174287d0a5ec66fe`.
- [x] CI run [#43962841690](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43962841690) completed successfully: backend tests passed, Ruff passed, Android debug build and APK artifact upload passed.
- [x] Added migration `005_reservation_response_link.sql`, checksum `f890cab29b59c1dd930041ef8af760a7dfa01bf09d48e1684377436652f652b8`. It adds a foreign-key response link and unique constraint, and backfills only exact window/page HTTP 200 evidence with one unambiguous match.
- [x] Captured HTTP responses are linked to their exact durable reservation in the same transaction as response/event persistence.
- [x] Resume replays the exact reservation-bound response only after validating request window/page/hash, provider/source/approval identity, matching request event, response status, JSON envelope, and raw-body SHA-256. Fixture observations and checkpoint remain atomic.
- [x] Added PostgreSQL integration regression test `test_resume_replays_reserved_response_without_repeating_provider_http`; complete CI passed.
- [x] Updated the manual collection workflow to run the checksum-verified migration runner against the dedicated `veltrix_ai_analyst` database before importer execution. It does not log credentials.
- [x] Read-only Neon query confirmed run 3 still has 24 reservations and all 24 HTTP 200 response events uniquely match their exact reserved window/page; the interrupted Aug 29–Sep 5 page has exactly one reservation. No writes/provider calls were made by this inspection.
- **Current state:** run 3 remains RUNNING in Neon; 23/34 checkpoints complete; 247 fixtures persisted; 24/40 requests reserved; the interrupted page awaits replay; 10 later windows pending; 0 quarantine rows at last inspection.
- **Next action:** manually dispatch [Controlled Brazil Serie B Historical Import](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/historical-brazil-serie-b.yml) with `confirm_collection=COLLECT_BRAZIL_SERIE_B` and `resume_run_id=3`. The workflow applies migration 005 first, then resumes run 3. Do not leave resume_run_id blank; that would start a new run.
- **No model training, odds collection, calibration, or prediction publication is enabled by this recovery.** The run must complete and its automatic validator must pass before the collected data is accepted.


### Neon migration 005 applied and run 3 recovery link verified — 2026-11-16
- [x] Applied `005_reservation_response_link.sql` to the dedicated Neon database `veltrix_ai_analyst` and inserted its exact checksum into `public.schema_migrations`.
- [x] Read-only verification: migration checksum matches; run 3 has 24/24 reservations linked to captured response IDs; interrupted Aug 29–Sep 5 page 1 links to response ID 24; 23 completed windows remain; 247 fixture rows remain; quarantine count is 0.
- [x] The migration backfill identified exactly one matching HTTP 200 response for every run 3 reservation. No provider HTTP calls were made and no fixture/checkpoint/run status rows were changed by the migration.
- **READY TO RESUME:** workflow [Controlled Brazil Serie B Historical Import](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/historical-brazil-serie-b.yml), select **Run workflow**, set `confirm_collection=COLLECT_BRAZIL_SERIE_B`, and set `resume_run_id=3`. Do not leave the resume ID blank.
- The workflow migration step is idempotent: it will verify migration 005's checksum and skip reapplying it, then resume run 3. The remaining 10 windows are within the existing 40-request budget; current usage is 24/40.
- Automatic post-import validation remains mandatory. Import is not yet complete or validated; no odds collection or model training is authorized.

### 5Dollar historical import — completed and automatically validated (2026-11-16)
- [x] Recovery workflow run [#43964327879](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43964327879), job [#133639654596](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43964327879/job/133639654596), completed successfully on 2026-11-16; workflow_dispatch resumed existing import run ID 3 on commit e1b7a426158b0312f65a4f6369494a93f2c608ee.
- [x] Migration verification succeeded; no unapplied migrations were reported.
- [x] Import run 3 completed all 34/34 weekly checkpoints over [2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z).
- [x] Final validator returned `passed=true`, status `COMPLETED`, 374 fixture rows and 374 fixture sightings, 374 inserted, 0 duplicates, 0 quarantined, 0 unresolved quarantines.
- [x] 34 provider requests used against the 40-request cap; all 34 request events have raw response evidence. No budget breach.
- [x] The captured-response recovery path reconciled the previously interrupted page without repeating its reserved HTTP request.
- [ ] **Data-use boundary remains:** provider publication/availability timestamps were not established. Imported observations are not eligible as pre-match training features, CLV evidence, or point-in-time backtests. Use for descriptive/result-history work only unless separate timestamp evidence establishes eligibility.
- [ ] Next stage: build source-quality/coverage and fixture canonicalization audits, then a strictly point-in-time feature eligibility pipeline. Do not train or publish predictions from this dataset as-is.
- [ ] AI Midas snapshot remains a separate descriptive candidate source with its own anomaly quarantine; do not merge it blindly with the 5Dollar import.


### Fixture coverage, identity and PIT gate audit — 2026-11-16
- [x] Read-only Neon audit of import run 3: 374 fixtures, 34/34 completed windows, each window count reconciles with its checkpoint; no empty windows.
- [x] Competition scope is provider ID `522514093` / Brazil Serie B. The provider catalogue row lacks country, season and last-fixture metadata; observed fixture counts do not prove schedule completeness.
- [x] Score/status audit: 370 FINISHED with complete scores; 4 UNKNOWN with no scores; no contradictory non-finished scores.
- [x] Team audit: 21 provider IDs; no blank names or missing FK links; 6 home and 3 away label differences are diacritic/transliteration variants. Flagged two separate IDs `America MG` / `América Mineiro` with a near-simultaneous Goiás fixture pair as an unresolved alias/duplicate candidate.
- [x] Duplicate audit: no exact duplicate provider IDs, no duplicate competition/kickoff/team-ID key groups, and no raw-name same-order near-time matches. The alias collision remains a separate unresolved candidate.
- [x] PIT audit: 0/374 source observations have publication or availability timestamps; 0 are PIT-certifiable. All 1,031 sightings are `RETRIEVED_AT_ONLY`, non-certifiable. The automatic validator's `non_pit_observations=0` field is not PIT certification.
- [x] Added the audit and canonical fixture design to `docs/ledger/2026-11-16-fixture-coverage-integrity-pit-audit.md`.
- [x] Added a pure fail-closed Python publication-evidence policy and unit tests.
- [x] Added migration `006_pre_match_feature_pit_gate.sql`: append-only pre-match feature input table with a database trigger requiring the exact sighting to have verified publication time, captured successful response, matching payload hash, availability before cutoff, and approved FEATURE_ENGINEERING + MODEL_TRAINING rights.
- [x] Added a PostgreSQL integration test for accepted publication evidence and rejected retrieval-only evidence.
- [ ] CI and review pending. Migration 006 is not applied to Neon; feature pipeline remains unimplemented and all current 5Dollar records remain excluded.
- [ ] Canonical team/competition/fixture tables and reviewed provider identity crosswalks are designed but not yet materialized. No automatic entity matching or merge is enabled.


## Latest verified database checkpoint — Migration 007 applied

- Controlled workflow [#44072112212](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44072112212) succeeded on main commit `3faf3d2ad2ceb293ce322b18ef662782426a2aaf`.
- Migration runner applied `007_canonical_entity_layer.sql`; Migration 006 was already applied with a matching checksum.
- Migration 007 checksum: `5503622ac57bd1875e08cf40cf1d87220cec99deb79e8fc23dd4ec6ebbffc30b`. Migration 006 checksum re-verified: `6b7b8d9385d66ec06079a9a8388b3d4f37c45da8ba6f47075166707b8831cb4f`.
- Database name check passed for `veltrix_ai_analyst`. Seven canonical tables, four functions and ten required triggers verified by the workflow.
- Canonical materialization is now the next stage. No canonical records were inserted during migration. Begin with dry-run/idempotency design and source provenance reconciliation. Keep the 374 source fixtures unchanged; all observations remain non-PIT-certified; America MG / América Mineiro remain unresolved; four UNKNOWN fixtures remain scoreless.
- No provider API requests, model training or prediction publication were performed by this migration workflow.


## Canonical materialization executed and independently verified — 2026-11-17

- [x] User-dispatched guarded production workflow [#44086857898](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44086857898), job [#134051435015](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44086857898/job/134051435015), completed successfully on main commit `e6ca720ca556c5cb6aea7e867075e841b0f7bf3e`.
- [x] Runner emitted `MATERIALIZATION_COMMITTED` and `CANONICAL_MATERIALIZATION_COMMITTED`; exact database identity was `veltrix_ai_analyst`.
- [x] Transaction reconciled before/after counts: canonical teams 0→21; competitions 0→1; fixtures 0→374; provider team identity links 0→21; provider competition identity links 0→1; fixture-source links 0→374; identity review events remained 0.
- [x] Runner reported 21 teams created, one competition created, 374 fixtures created, zero fixtures reused, zero identity reviews, zero PIT promotions, and zero provider HTTP requests. Plan remained exact: 5DollarFootballAPI Brazil Serie B `522514093`, import run 3; 370 FINISHED, four UNKNOWN; conflicts `2341822348` and `3116209225`; 396 non-PIT observations.
- [x] Independent read-only Neon query against project `young-wind-27772160`, database `veltrix_ai_analyst`, independently confirmed all seven canonical table counts exactly match the workflow report; `pre_match_feature_observations=0`.
- [x] Independent status audit: 21 team links and one competition link remain `REVIEW_REQUIRED`; all 374 fixture-source links remain `REVIEW_REQUIRED`; all 374 fixtures remain `SOURCE_ROW_ONLY`; two fixtures are `CONFLICT`, 372 are `IDENTITY_REVIEW_REQUIRED`; 370 fixtures are FINISHED and four UNKNOWN.
- [x] Independent source audit confirmed 374 fixture/result observations and 374 sightings, with zero PIT-certifiable observations and zero PIT-certifiable sightings.
- **Current stage:** Canonical source-row materialization is complete. Next stage is evidence-backed historical identity review and source/season coverage reconciliation, followed by rights/PIT eligibility work.
- **Hard restrictions:** Do not auto-verify or merge team identities; do not clear the two fixture conflicts without independent evidence; do not use the 396 non-PIT observations or source-row-only canonical fixtures as pre-match features; no model training, calibration, prediction publication or production API is authorized.
- Android runtime testing and typed backend integration remain deferred until the appropriate later stage and real prediction endpoints exist.


## Stage 3 execution checkpoint — architecture, contracts and PIT admission (2026-11-17)

- [x] Repository isolation audit: confirmed this is the independent `Nexora-Apparel/veltrix-ai-analyst` repository with its own FastAPI backend, Android client and dedicated `veltrix_ai_analyst` Neon database. No legacy prediction engine is present in the inspected backend; the prediction implementation starts from a clean module boundary.
- [x] Architecture decision record added: [ADR-001](ADR-001-PREDICTION-ENGINE-ARCHITECTURE.md). It defines contracts/features/models/validation/predictions/registry boundaries, identity and rights gates, model progression, Elo/Poisson/Dixon–Coles mathematical conventions, chronological evaluation and abstention.

## 2026-11-18 — Matched model comparison and calibration disposition

- [x] Uncalibrated matched fixed-v1 vs nested-v2 workflow [#44172376777](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44172376777), job [#134356040176](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44172376777/job/134356040176), completed successfully.
- [x] Post-PR #41 fold-contained calibrated matched workflow [#44173473173](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44173473173), job [#134364071899](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44173473173/job/134364071899), completed successfully; private artifact persistence was idempotent.
- [x] Both comparisons used 305 identical held-out fixtures across 12 chronological folds (75 initial training fixtures); simultaneous kickoff groups remained intact.
- [x] Raw matched metrics: fixed v1 Brier **0.6081835337**, log loss **1.0153185492**; nested v2 Brier **0.6124461060**, log loss **1.0215836752**.
- [x] Paired raw differences (v2 minus v1): Brier **+0.0042625722**, 95% fold-block interval **[+0.0009324064, +0.0084349691]**; log loss **+0.0062651260**, interval **[+0.0013073868, +0.0120188047]**. Positive favours fixed v1. Bootstrap is exploratory with only 12 fold blocks.
- [x] Fold-contained temperature scaling worsened Brier and log loss for both models: v1 calibrated Brier/log loss **0.6121281399 / 1.0204752553**; v2 **0.6131554044 / 1.0222996566**. ECE improved in some diagnostics, but primary metrics worsened.
- [x] Calibrated paired differences v2 minus v1: Brier **+0.0010272646**, 95% interval **[-0.0016028217, +0.0044331101]**; log loss **+0.0018244013**, interval **[-0.0016913271, +0.0065814643]**. Both intervals include zero.
- **Research disposition:** fixed v1 remains the benchmark candidate; preserve v2 as an immutable comparator; do not use temperature scaling as the default. Neither is production- or PIT-certified.
- **Restrictions unchanged:** one competition/season; unresolved identity/duplicate cases; no timestamped odds benchmark or prospective paper validation; no production endpoint, Android prediction integration, value-bet activation or public forecast publication. Android work remains deferred until real prediction endpoints exist.
- Full metrics and limitations: [retrospective model screening ledger](ledger/2026-11-17-retrospective-model-screening.md#matched-v1-v2-evaluation-and-fold-contained-calibration--completed-2026-11-18).


## 2026-11-18 — Provider access verification and bounded odds probe preparation

- [x] User-dispatched provider-access workflow [#44214433784](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44214433784), job [#134500596876](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44214433784/job/134500596876), completed successfully. Existing API key authenticated; account plan is Community; daily request limit 300; rate window 3,600 seconds; burst limit 20/minute; usage at check time 0.
- [x] Brazil competition listing returned two entries: Serie A 3118717965 and Serie B 522514093. The existing Community account's Brazil coverage is therefore visible; no new account/key was created.
- [x] Public plan documentation confirms Community Access includes the top-five leagues plus one country pack, Bet365 odds markets, and 12 months of results/odds. The fixture odds snapshot endpoint is the intended first probe. Full odds tick history remains Ultra-only; do not call it with the current plan.
- [x] PR #42 merged at 36b10411d73d3ecd41c7a239ef6412adaef3bc49: documented fixture-odds and history adapters, Bet365-only timestamped 1X2 snapshot admission, fixed-goal-line history dispatch, separate source tick/retrieval clocks. Backend tests, Ruff and Android debug APK CI all passed.
- [x] PR #43 merged at e54dce54b8319560a89e86847652b0d0a726e5fd: manual-only one-request odds snapshot probe workflow and compact response manifest. CI passed backend tests, Ruff and Android debug APK build.
- [x] Manual probe run [#44216129899](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44216129899), job [#134506317580](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44216129899/job/134506317580), completed successfully on main commit `14b7004fdaf7e2c1b7e29a2e4435154686b157b2`.
- [x] Exactly one `GET /v1/fixtures/1194891794/odds` request returned HTTP 200; zero retries and zero pagination. Bet365 (`bet365`) returned 12 markets: `1x2`, `asian_handicap`, `asian_handicap_half`, `btts`, `card_asian`, `card_line`, `corner_asian`, `corner_line`, `corner_line_half`, `goal_line`, `goal_line_fixed`, and `goal_line_half`.
- [x] Bet365 1X2 opening snapshot: home 4.10, draw 3.25, away 1.90; `opened_at=2026-11-09T13:15:09+00:00`. Response HTTP Date `2026-11-18 01:29:05 GMT`; retrieval `2026-11-18T01:29:05.859374+00:00`; response SHA-256 `93c40815c5c587e253cafd2ecbdb55521787ecb9bf1c43611f4fff52b5cf0180`. Rate-limit remaining header was 297/300. Compact manifest artifact ID `14388467126`, SHA-256 `fb66e597e00dd680941ec9da241afe5fe24da133de8ba58806ee1fb1ed67b7e5`, expires 2026-11-25.
- [x] Probe establishes authenticated endpoint access and a real Bet365 1X2 opening field, not PIT eligibility. This fixture's opening timestamp predates retrieval by over eight days; retrieval after the opening cannot prove when the odds were first available to this system. The observation is not eligible for a historical pre-match cutoff or CLV benchmark.
- [ ] Next: implement a manual-only, bounded prospective odds capture design that records retrieval time at request receipt, request start/end, response hash, fixture kickoff, prediction cutoff, provider/bookmaker/market/selection/line, and source timestamp separately. Admit only observations actually retrieved before the prediction cutoff; never backfill availability from `opened_at` or provider tick timestamps. Validate schema and idempotency before any DB write or recurring schedule.
- Restrictions unchanged: no odds pipeline activation, production prediction endpoint, Android/backend prediction integration, model promotion, value-bet activation or public forecast publication. Retrospective corpus remains non-PIT-certified.
- Restrictions unchanged: no odds pipeline activation, production prediction endpoint, Android/backend prediction integration, model promotion, value-bet activation or public forecast publication. Retrospective corpus remains non-PIT-certified.


## 2026-11-18 — Bet365 odds snapshot access confirmed

- Probe evidence and interpretation are recorded above. The successful snapshot is a provider-access/schema confirmation only; it does not certify historical availability, price freshness at the model cutoff, CLV, or betting value.
- [x] Prospective capture contract documented in [2026-11-18-prospective-odds-capture-contract.md](ledger/2026-11-18-prospective-odds-capture-contract.md), commit `668cdf7da6c7fa36bc44819b59237e435e4994e4`. It separates source tick time, retrieval time, provider Date, kickoff and prediction cutoff; defines fail-closed PIT admission, a one-fixture manual-only initial envelope, quota limits, and a test-first implementation sequence.
- **Next engineering unit:** implement pure typed capture contracts and boundary/schema tests only; do not add a database writer, recurring schedule, or model feature activation yet. Keep capture manual and low-volume, keep the current Community quota budget, and do not create a recurring workflow or database writer until contract tests establish strict cutoff, source provenance, duplicate/idempotency, and rights gates.
- Existing research model disposition is unchanged: fixed v1 remains the retrospective benchmark candidate; v2 remains an immutable comparator; neither is PIT-certified or production-certified.


## 2026-11-18 — Secondary odds provider candidate identified

- The reference repository `Nexora-Apparel/veltrix-football` contains a live-verified The Odds API v4 integration in `app/provider_adapters.py`, using the secret name `THE_ODDS_API_KEY`. It requests soccer events, bookmaker h2h/totals snapshots, and event-specific BTTS; records bookmaker `last_update`, decimal prices, outcomes, optional points/lines and quota headers. Reference provider register reports historical live authentication/market checks, not current key balance or current plan.
- The reference project's provider qualification sampled 77 5Dollar Community market blocks across seven competitions; 7/77 (9.09%) had market timestamps, and its BTTS history request returned HTTP 403. This is not a fresh AI ANALYST cross-league audit, but means Community snapshot access alone must not be presumed sufficient for 98% timestamped coverage.
- AI ANALYST's current single-fixture probe proves one Bet365 opening snapshot only; it does not prove broad coverage or historical PIT availability.
- Candidate decision: keep 5Dollar as canonical fixture/results source and first odds source; qualify The Odds API v4 as a supplemental bookmaker-price source. Do not enable it yet. OddsPapi, InferSports and suspended API-Football are not added to this provider decision.
- Qualification design: [2026-11-18-supplemental-odds-api-qualification.md](ledger/2026-11-18-supplemental-odds-api-qualification.md), commit `7a105a4db54e4a9770da2242786ca4666471bc89`.
- Credential boundary: `THE_ODDS_API_KEY` is a repository-scoped GitHub secret in the reference integration. It is not automatically available in AI ANALYST. No key values were accessed, copied, or logged. Before a live AI ANALYST request, the intended credential must be configured in that repository's own secret store; reuse the existing credential only, subject to current plan, balance and terms. No new account or purchase.
- Next: add a manual, credential-safe, zero-odds-credit `/v4/sports` check to AI ANALYST. It must never expose the key. If that check authenticates, proceed with one fixture-specific, minimal-market live odds probe, recording quota cost and both provider and local timestamps. No DB writes, schedules, model features or value-bet activation.


## 2026-11-18 — The Odds API authentication and cross-provider qualification implementation

- [x] User-dispatched The Odds API catalogue probe [#44220418309](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44220418309) completed successfully. `GET /v4/sports/` returned HTTP 200 and `AUTHENTICATED_SOCCER_CATALOGUE_AVAILABLE`, with 46 active soccer sport keys.
- [x] Verified quota headers from that run: `quota_last_cost=0`, `quota_used=229`, `quota_remaining=271`. This is the observed balance at 2026-11-18 02:03:30 UTC, not a guarantee of the balance after subsequent requests. No odds credits were consumed by this catalogue check.
- [x] User explicitly authorized use of the existing Odds API account as needed for this project. Use remains bounded by available credits, provider terms, approved sport scopes, and strict provenance/PIT rules; commercial use remains disallowed under the recorded source approval.
- [x] PR #47 merged strict offline event-to-fixture matching. It preserves separate provider IDs, requires exact home/away orientation and kickoff within five minutes, and rejects aliases, reversed teams, drift and ambiguity.
- [x] PR #48 merged cross-provider fixture catalogue qualification. It compares one selected competition over the next 30 days using one Odds API events request and one 5Dollar scheduled-fixture request; no odds markets, retries, pagination, or DB writes.
- [x] PR #48 CI [#44222974563](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44222974563) passed: 209 backend tests, Ruff lint, and Android debug build.
- [ ] Manual dispatch of the merged [Cross-provider fixture catalogue qualification workflow](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/the-odds-api-5dollar-fixture-qualification.yml) remains outstanding. Start with one competition (Premier League default) and inspect both provider manifests plus the offline match manifest. This workflow spends zero Odds API odds credits.
- [ ] If and only if both catalogues are complete and exactly one fixture match is returned, perform one event-specific `h2h` market request in one region, record the exact quota cost, response hash, local retrieval timestamp and bookmaker quote timestamps. The workflow candidate flag is not authorization to ingest or activate the observation.
- Restrictions unchanged: no DB writer, recurring collection, feature activation, CLV claim, value betting, production prediction endpoint, public forecast publication, model promotion or Android/backend prediction integration. Existing model artifacts remain retrospective and non-PIT-certified.


## 2026-11-18 — Odds API exact-match h2h qualification gate merged

- [x] PR #49 merged as `69bd04666996c3d0901105ebdb3d1a45dd3e4522`: strict event-specific h2h response parser and tests.
- [x] PR #49 CI run [#44224263834](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44224263834) passed: 214 backend tests, Ruff, Android debug build.
- [x] Parser validates event ID, sport key, home/away orientation and exact canonical fixture kickoff alignment. It uses market-level `last_update`, rejects future quote ticks, and only retains complete timestamped HOME/DRAW/AWAY bookmaker sets.
- [x] PR #51 merged as `b1db56bda8bcaa9e82ac0619f1b0dc8227bf6392`: after complete catalogues and exactly one unique exact fixture match, the manual workflow is authorized to make one event-specific `h2h` request in one region (UK). Maximum expected cost is one odds credit; no retries, pagination or other markets.
- [x] PR #51 CI run [#44224521063](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44224521063) passed: 214 backend tests, Ruff, Android debug build.
- [ ] Manual dispatch of [Cross-provider fixture catalogue qualification](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/the-odds-api-5dollar-fixture-qualification.yml) remains required. Choose one competition (Premier League default). It makes one 5Dollar fixture-list request and one quota-free Odds API events request; only if both catalogues are complete and one unique exact match exists does it make one h2h market request (expected one credit).
- [ ] Inspect the three catalogue/match/market manifests. Confirm actual quota cost from response headers and whether the Odds API adds meaningful bookmaker/market/timestamp coverage beyond 5Dollar Bet365.
- [ ] After the single market probe, audit rights, source timestamp quality and PIT availability before any persistence or model feature work.
- Restrictions unchanged: no database writes, recurring collection, historical odds calls, feature activation, CLV claims, value betting, production prediction endpoint, public forecast publication, model promotion or Android/backend prediction integration. Existing v1/v2 models remain retrospective and non-PIT-certified.


- [x] PR #52 merged as `30f4036b819c901ce4404b5ff65336fec992344c`: the one-event probe now parses the actual `x-requests-last` header, records `actual_quota_cost`, and flags missing/invalid or over-cap values. Zero-cost empty responses and one-credit responses are both within the allowed cap.
- [x] PR #52 CI run [#44224762047](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44224762047) passed: 214 backend tests, Ruff, Android debug build.


## 2026-11-18 — Prediction and value-betting architecture clarified; ledger reconciled

- [x] User-confirmed governing rule recorded in [prediction/value-betting separation ledger](ledger/2026-11-18-prediction-and-value-betting-separation-reconciliation.md): bookmaker odds are primarily for the secondary value-betting subsystem, not required inputs to the core prediction engine.
- [x] Core predictions must be generated independently from eligible football data and the statistical/ML ensemble. Bookmaker prices must not act as hidden priors, overrides or required dependencies.
- [x] Value betting consumes independent model probabilities plus eligible bookmaker prices. Missing, stale, invalid or insufficient odds suppress only the value-bet recommendation, never an otherwise eligible prediction. No forced bets when no qualifying edge exists.
- [x] Reconciled prior foundation, Neon/migration and bounded-import controls, Brazil Serie B retrospective data audit, model artifacts/evaluations, PRs #47–#54, Odds API/5Dollar qualification run #44228137046, quota accounting and remaining blockers in the dated ledger entry.
- [ ] Outstanding same-fixture provider comparison: one 5Dollar Bet365 snapshot for fixture `4042864659`; no second Odds API request is needed for this comparison.
- Restrictions unchanged: no production prediction publication, odds persistence/recurring collection, model promotion, value-bet activation or Android/backend prediction integration until their separate gates pass.


## 2026-11-18 — Bookmaker odds isolation and value-betting capture contract corrected

- [x] PR [#55](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/55) merged as `8acdb7083180c87420d6e1371b8fad5e985aa5c6`.
- [x] Bookmaker odds observation contracts are explicitly restricted to `VALUE_BETTING_ONLY`; the incorrect model-training rights flag was removed.
- [x] Capture contracts preserve request-start, local-retrieval, provider-response Date, source-tick, kickoff and prediction-cutoff timestamps independently.
- [x] Core prediction feature admission now rejects `BOOKMAKER_ODDS` and unknown data domains; regression tests cover both fail-closed paths.
- [x] CI run [#44236392864](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44236392864) passed backend tests, Ruff lint and Android debug build.
- [x] Detailed evidence: [bookmaker odds isolation PR #55 ledger](ledger/2026-11-18-bookmaker-odds-isolation-pr55.md).
- [ ] Provider-specific bookmaker-odds rights must be reviewed and approved for the exact data type, provider scope and value-betting purpose. The contract's rights gate does not itself grant permission.
- [ ] Next: implement a registry-backed rights decision adapter, then a dry-run one-fixture capture envelope with idempotency tests. No database writer, recurring schedule, odds-derived model features or value-bet activation until those gates pass.
- **Architecture invariant:** bookmaker odds remain excluded from core prediction generation. An odds failure may suppress a value-bet recommendation only; it must not suppress an otherwise eligible independent football prediction. Value betting remains locked pending separate certification.


## 2026-11-18 — Historical corpus audit and retrospective research pipeline

- [x] PR #58 merged: manual 5Dollar odds capture dry-run validator. Latest-head CI passed backend tests, Ruff and Android debug build.
- [x] PR #59 merged: exact raw odds response retention requirements. Manifest-only odds artifacts are metadata-only, not raw-response verified or PIT evidence.
- [x] PR #60 merged: read-only live Neon historical corpus qualification audit.
- [x] PR #61 merged: reproducible SELECT-only historical corpus audit SQL.
- [x] PR #63 merged: CBF-backed 21-row provider team identity review matrix. All candidate mappings remain REVIEW_REQUIRED; the America MG / América Mineiro alias is not merged.
- [x] PR #62 merged as `171d1565cb66b2a0691e55bdf488e75dc6da2ebf`: provider-local retrospective Elo / smoothed attack-defence Poisson / Dixon-Coles / adaptive ensemble, read-only Neon training runner, regression tests and manually dispatched research workflow.
- [x] PR #32 closed as superseded by the clean current-main port in PR #62.
- [x] Current-main CI for PR #62 head `2a84c15a7c46e3f20b97b0dc2ba1143e6d48f58d`: 255 backend tests passed, Ruff passed, Android debug build passed.

### Live Neon corpus qualification snapshot

Read-only audit of Neon project `veltrix-ai-analyst-db`, database `veltrix_ai_analyst`:

- 384 provider fixture rows: 380 FINISHED with scores, 4 UNKNOWN without scores.
- 384 fixture/result source observations and 384 sightings; every one lacks `source_published_at` and `available_at`; zero are PIT-certifiable.
- 384 canonical fixtures: 382 IDENTITY_REVIEW_REQUIRED and 2 CONFLICT; all SOURCE_ROW_ONLY.
- 384 fixture source links: source provenance verified, but all remain SOURCE_FIXTURE_REVIEW_REQUIRED.
- 21 provider team links: source provenance verified, but all remain REAL_WORLD_IDENTITY_REVIEW_REQUIRED.
- One competition link remains REAL_WORLD_IDENTITY_REVIEW_REQUIRED.
- Outstanding review inventory: 20 team identity candidates, one alias candidate, one competition identity candidate, four duplicate fixture candidates, one season coverage reconciliation case and one PIT timestamp gap.
- No Neon data was modified. No provider request or odds API credit was used for this audit.

### Next execution gates

1. Manually dispatch the [Retrospective model training workflow](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/retrospective-training.yml) with `RUN_RETROSPECTIVE_RESEARCH`. The workflow reads Neon in a READ ONLY transaction and uploads a private retrospective report. This manual dispatch is not available through the current GitHub action controls in this session.
2. Inspect the report's row counts, exclusions, report hash, scorecards, rho and adaptive ensemble weights. These full-corpus prequential metrics are exploratory and are not directly comparable to the existing 305-fixture nested walk-forward evaluation.
3. Keep all outputs RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED. Do not promote a model or enable production predictions from this report.
4. Continue the full 370-FINISHED-row CBF fixture-by-fixture schedule reconciliation and human identity decisions. Preserve all source rows and unresolved provider IDs.
5. Keep the PIT timestamp gap open unless authoritative source-publication/availability evidence is found. No kickoff or retrieval timestamp substitution.
6. Keep Android integration deferred until genuine prediction endpoints exist; keep value betting locked pending separate certification.



## Latest execution checkpoint — effective shrinkage audit and two-tier admission contract (2026-11-21)

- [x] PR [#138](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/138) merged as `d1c55fffe078ebf78910ea75195083984f079a15`. Its exact head `6acca21d7e0ec87496d13a781651bb7add73108d` passed CI run [#44892716222](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44892716222): 496 backend tests passed, Ruff passed, Android debug build passed.
- [x] Added `backend/app/research/effective_shrinkage_audit.py` and a synthetic report-structure test. The audit emits per-team attack/defence fitted effects, near-unpenalized references, signed ratios and prior/data-information ratios. It does not change model fitting or production behavior.
- [x] Independent numerical reproduction of archived run #44873166128 / artifact 14694089682 against Stage 6 dataset artifact 14694463354 matched all 25 archived expected-goal rates within approximately 1.1e-7.
- [x] Effective runtime confirmed from the archived artifact: team_ridge=0.5, competition_ridge=0.5, half-life=365 days. The function default competition_ridge=2.0 was not the runtime value.
- [x] 996 training-only labels, 136 teams, seven competitions; total recency weight 868.5811214801818; summed-objective team tau 434.2905607400909.
- [x] Median absolute attack effect retained versus near-unpenalized fit: 3.11%; defence: 3.39%. Median signed ratios: 3.01% attack and 3.28% defence; sign agreement 90.44%/91.18%. Median prior/data-information ratios: 30.58x attack and 30.31x defence. This supports severe over-regularization but is not predictive validation and does not select replacement hyperparameters.
- [x] Production API read-back: `/v1/research/predictions` HTTP 200, MODEL_QUARANTINED, NOT_PUBLISHED, zero predictions, promotion/value locked; `/v1/predictions` HTTP 200, zero predictions. Latest production deployment remained READY at commit `95445c9b7aaba045f15a97afe443211da341a2fe`; no deployment was triggered by this audit.
- [x] 5Dollar Community terms/docs reviewed: last 12 months of results/odds; 300 requests/hour and 20/minute burst limit. Two complete prior seasons are not available under the current Community history entitlement. No purchase or provider request was made.
- [x] Existing 28 identity/reconciliation cases remain unresolved. No cross-season identity stitching, alias promotion or provider-ID rewrite is permitted before evidence-backed resolution.
- [x] Dated ledger entry: [2026-11-21 effective shrinkage audit](ledger/2026-11-21-effective-shrinkage-audit.md).
- [ ] Execute the new per-team CLI against the actual archived artifacts and retain its complete per-team report; current headline numbers are from an independent offline numerical reproduction.
- [ ] Implement synthetic recovery/shrinkage tests that fail the current 0.5/0.5/365 configuration and an excessive-prior negative control.
- [ ] Implement the approved two-tier admission registry, hash immutability, controlled forecast write function, application-role INSERT revocation and API read-time admission join.
- [ ] Draft the primary 1X2 log-loss threshold, MDE/power and baseline comparison protocol for explicit user approval; final holdout is single-use.
- [ ] Design Community-bounded season backfill only after resolving identity mapping and confirming each competition's accessible season coverage.
- **Release state unchanged:** model QUARANTINED; no production forecasts; value betting LOCKED; Android UI preserved. No Neon writes, provider calls, Odds API credits or production deployment were used for this work.


## Latest execution checkpoint — regularization contract tests and database admission audit (2026-11-21)

- [x] Opened PR [#139](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/139), branch `research/regularization-contract-tests`, latest head `6ac289436af299887143ed124ed10e5e9ab40413`. PR remains open and unmerged.
- [x] Added `docs/ML_REGULARIZATION_CONTRACT.md`, the pseudo-match scale helper, and deterministic synthetic tests. Current quarantined 0.5/0.5/365 configuration is rejected by recovery/shrinkage gates; the excessive-prior negative control is also rejected.
- [x] CI run [#44893189043](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44893189043) passed: 504 backend tests, Ruff, Android debug build and APK upload.
- [x] Read-only Neon audit found 0 published prediction rows, one research shadow run, and two model artifacts. The research run's model_version is nullable; there is no model_versions table or FK; report hash is required but not bound to admission. Research runs have append-only UPDATE/DELETE triggers but no INSERT admission trigger. Predictions have a pre-match INSERT trigger but no admission check.
- [x] DB grants show direct INSERT for neondb_owner on forecast tables; no dedicated restricted application role/controlled-write boundary is present in the visible grants. This is a confirmed database architecture gap, not an applied migration.
- [x] Production API read-back at 10:13:40 UTC: research endpoint HTTP 200 MODEL_QUARANTINED/NOT_PUBLISHED/zero predictions; published endpoint HTTP 200/zero predictions. Production deployment remains READY at commit `95445c9b7aaba045f15a97afe443211da341a2fe`; no deployment created for PR #139.
- [x] Dated ledger entry: [2026-11-21 regularization contract and DB audit](ledger/2026-11-21-regularization-contract-and-db-audit.md).
- [ ] Wire the pseudo-match scales into a separate candidate fitter; add tests showing the corrected candidate passes recovery while current and excessive-prior controls fail.
- [ ] Implement the independent primary 1X2 log-loss evaluator, MDE/power, both baselines, date-block bootstrap and immutable run log.
- [ ] Design the model_versions registry and two-tier SHADOW/PUBLISHED database enforcement, including immutable hashes, restricted application role, controlled write function and API read-time admission join.
- [ ] Draft thresholds for explicit user approval; do not freeze numeric thresholds or k values without sign-off.
- [ ] Resolve/quarantine the 28 identity cases and verify 5Dollar Community per-competition history coverage before any cross-season backfill.
- **Release state unchanged:** model QUARANTINED, no production forecasts, value betting LOCKED, Android UI preserved. No DB writes, provider requests, Odds API credits or production deployment.


## Latest design checkpoint — two-tier database admission enforcement (2026-11-21)

- [x] Drafted [MODEL_ADMISSION_DB_CONTRACT.md](MODEL_ADMISSION_DB_CONTRACT.md) from live read-only schema evidence. It defines SHADOW/PUBLISHED tiers, ADMITTED/QUARANTINED status, immutable hashes, monotonic transitions, model-version binding for both research runs and published predictions, SECURITY DEFINER controlled writers, least-privilege runtime role, and read-time admission-aware API views.
- [x] Current database evidence confirms `model_versions` does not exist. The two `model_artifacts` rows are legacy `attack-defence-poisson-v1` and `attack-defence-poisson-v2-nested-tuned` artifacts (380 fixtures/20 provider teams); neither is the current `hierarchical-poisson-shadow-v1` run (996 labels/136 teams). Do not attach the current run to either legacy artifact.
- [x] Existing research run already has a required report_sha256 value, but its model_version column is nullable at schema level and has no registry FK. Its append-only triggers protect UPDATE/DELETE only; no admission-controlled INSERT trigger exists.
- [x] Current published predictions table has zero rows. Current research-shadow run is preserved as QUARANTINED when registry backfill is designed; never mark it ADMITTED based on its prior SHADOW_FORECASTS_READY status.
- [ ] Compute and independently verify the current shadow config SHA from the immutable archived report/config before any migration backfill. Never invent the hash.
- [ ] Build migrations and disposable-Neon-branch tests first. No production migration, role creation, Vercel secret rotation, or database write has been performed.


## Verification refresh — PR #139 latest head (2026-11-21)

- [x] Latest PR #139 head `edb41a13cbaeedd11eb143c311de5e12407b0da2`; six commits ahead of main, zero behind.
- [x] Latest CI run [#44893501873](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44893501873) passed both jobs: 504 backend tests, Ruff, Android debug build and APK upload.
- [x] The PR remains open and unmerged. Vercel reports `build-rate-limit`; no preview deployment was found and production deployment remains unchanged.
- [ ] The archived per-team CLI workflow has been added to the review branch, but its push-triggered execution has not been independently verified. Do not claim a full 136-team report until its run and artifact are read back.
- [x] DB admission design is documented in [MODEL_ADMISSION_DB_CONTRACT.md](MODEL_ADMISSION_DB_CONTRACT.md); no production migration or write has been applied.


## Archived per-team shrinkage CLI verified (2026-11-21)

- [x] Workflow run [#44893869016](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44893869016) successfully downloaded the immutable forecast and Stage 6 artifacts, ran the repository's exact `effective_shrinkage_audit` CLI, and verified `FIT_REPRODUCTION_VERIFIED`.
- [x] Full report contains all 136 team rows across seven competitions, based on 996 training-only labels. Report artifact ID `14703192024`; SHA-256 `4997f0b6a93c2fc02c1a164c2daff33e2dd532b8b50b57a35a41ec609e64fab0`.
- [x] Exact CLI results: median absolute attack ratio 3.110425%; defence 3.393930%; median prior/data information 30.57635× attack and 30.30684× defence; effective runtime team_ridge=0.5, competition_ridge=0.5, half-life=365; summed-objective team tau=434.29056074.
- [x] Signed median ratios: attack 3.006544%, defence 3.277747%; sign agreement 90.44% and 91.18%. Absolute-ratio P10–P90: attack 1.327%–8.863%; defence 1.657%–9.433%.
- [x] The exact repository CLI output matches the independent numerical reproduction. This is a fit/shrinkage diagnosis, not predictive validation or a selected replacement k.
- [x] Full per-team report is available from [workflow run #44893869016](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44893869016).


## Candidate fitter and archived CLI execution checkpoint (2026-11-21)

- [x] Added research-only `backend/app/models/hierarchical_poisson_v2.py` to PR #139. It uses the unnormalized weighted Poisson NLL, common pseudo-match k values, per-competition team effects, explicit competition/global home priors, and no unvalidated defaults. It is not wired to production inference.
- [x] Added a synthetic candidate recovery test alongside current-configuration and excessive-prior rejection controls. Candidate test is awaiting the latest CI run.
- [x] Archived audit workflow [#44893869016](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44893869016) completed successfully and uploaded the 136-team report artifact 14703192024 (SHA-256 `4997f0b6a93c2fc02c1a164c2daff33e2dd532b8b50b57a35a41ec609e64fab0`).
- [x] PR #139 metadata read-back: open, unmerged, mergeable; current head `940ae2f025e1feb1552bdda58cef5f73d028a0d0`. Latest preview deployment `dpl_H5UX1RbMTdMaDFNygvYUKqmZD9Gq` is READY for this branch only. No production deployment.
- [ ] Latest standard CI run #44893869028 is still pending with no jobs exposed yet; do not merge until backend tests/lint and Android debug build complete on this exact head.
- **Production remains unchanged:** API research feed MODEL_QUARANTINED/NOT_PUBLISHED/zero forecasts; published feed zero forecasts; Neon tables unchanged. No provider calls, Odds API credits or database writes.


## Final production read-back after PR #139 preview (2026-11-21 10:23:43 UTC)

- [x] Production research API: HTTP 200, MODEL_QUARANTINED, NOT_PUBLISHED, zero forecasts, promotion/value locked.
- [x] Production published API: HTTP 200, zero forecasts.
- [x] Production Vercel deployment remains READY at `dpl_4qjTXEBsVXHxJ13Ap7fjX7Zmk8b4`, main SHA `95445c9b7aaba045f15a97afe443211da341a2fe`.
- [x] PR #139 preview `dpl_H5UX1RbMTdMaDFNygvYUKqmZD9Gq` is READY at head `940ae2f025e1feb1552bdda58cef5f73d028a0d0`; preview-only.
- [ ] Standard CI #44893869028 remains pending with no job details. The 504-test pass on #44893501873 predates the v2 candidate fitter; do not merge until latest-head checks complete.


## Next architecture component drafted — independent evaluator (2026-11-21)

- [x] Drafted [INDEPENDENT_EVALUATOR_CONTRACT.md](INDEPENDENT_EVALUATOR_CONTRACT.md): single primary 1X2 log-loss metric, both required baselines, nested chronology, pre-evaluation MDE/power, paired date-block bootstrap, single-use final holdout, immutable run ledger, and secondary-market sequencing.
- [ ] Implement evaluator code separately from model-building code, with independent tests for probability scoring, fold chronology, label-observed cutoffs, date-block bootstrap, MDE/power, baseline comparison, and single-use holdout enforcement.
- [ ] Draft numeric thresholds for explicit user approval; no threshold hash is frozen yet.


## Candidate optimizer correction — validation remains open (2026-11-21)

- [x] CI #44893869028 exposed a real failure: 504 tests passed, but the new v2 synthetic recovery test failed at the optimizer line search. Android debug build passed; Ruff was skipped after the test failure.
- [x] Corrective commit `3c07aacb8fdc1dfd4832d1779d91ac4eaed98963` raises only the candidate optimizer numerical tolerance from 1e-7 to 1e-6 and adds iteration/gradient-norm diagnostics. No admission or performance threshold was relaxed.
- [ ] Latest CI #44894364730 is pending on the correction commit. Require full backend tests, Ruff and Android build to pass before merging.
- [x] No new Vercel deployment was created for 3c07; the last preview remains READY on 940ae2f. Production deployment/API remain unchanged and quarantined.


## Backfill and identity evidence — 2026-11-21

- [x] Verified Community Access terms: last 12 months of results/odds, top-five leagues plus one country pack, 300 requests/hour and 20/minute burst cap; public free-plan products require attribution and raw-data redistribution is prohibited. No provider calls, plan purchase or Odds API credits used.
- [x] Production DB read-back: 28 identity review cases are now `AUTOMATED_CONFIRMED` under recorded policy; one additional PIT timestamp gap is deferred. This is not equivalent to blanket cross-season identity clearance.
- [x] 20 Brazil Série B team real-world crosswalks are marked `REAL_WORLD_IDENTITY_VERIFIED` using full 380-fixture CBF schedule reconciliation. Another 116 links are only `SOURCE_IDENTITY_REVIEWED`, not real-world identity verified.
- [x] One remaining provider identity conflict: 5Dollar provider team ID `3808811746` (América Mineiro), link 16; exclude from cross-season stitching until independently resolved.
- [x] New v2 candidate now abstains when either competition-scoped team has zero match history; test added. The candidate remains research-only.
- [ ] Continue optimizer convergence work: the latest CI run #44894997224 failed the candidate synthetic recovery test at 4,000 iterations (gradient norm 2.51062e-5). Increasing the iteration budget/learning rate is under test; do not claim candidate recovery until CI passes.
- [ ] Next CI run #44895139262 is pending at this checkpoint; Android build and backend test job results must be read back individually.
- [x] Detailed findings recorded in [2026-11-21 regularization and DB audit ledger](ledger/2026-11-21-regularization-contract-and-db-audit.md).


## Independent evaluator pre-registration draft (2026-11-21)

- [x] Drafted [INDEPENDENT_1X2_EVALUATOR_PREREGISTRATION_DRAFT.md](INDEPENDENT_1X2_EVALUATOR_PREREGISTRATION_DRAFT.md).
- [x] Primary endpoint fixed conceptually to 1X2 log loss only; secondary markets are non-regression checks after primary passes.
- [x] Both mandatory baselines specified: league climatology with home advantage and a tuned team-aware Poisson/Elo baseline.
- [x] Chronological nested development, MDE/power before holdout, paired date-block bootstrap, one-use final holdout and immutable evaluation-run logging specified.
- [x] Evaluator must accept predictions/labels and must not import model fitting or feature-generation code.
- [ ] Numeric thresholds remain unapproved and unfrozen. Suggested alpha=0.05/power=0.80 are draft-only. No final holdout access is permitted until the user approves and the protocol hash is frozen.
