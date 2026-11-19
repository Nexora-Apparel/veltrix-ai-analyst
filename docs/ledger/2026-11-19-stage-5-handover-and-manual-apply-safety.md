# VELTRIX AI ANALYST — Stage 5 reconciliation and cross-stage handover

**Date:** 2026-11-19  
**Prepared at:** approximately 12:04 WAT  
**Repository:** `Nexora-Apparel/veltrix-ai-analyst`  
**Base checkpoint:** `ca71ebdefa0b1c906a9eafd2d42611c9d0588946`  
**Purpose:** preserve the exact state, rationale, evidence, safety boundaries and next actions for continuation in a new session.

## 1. Executive status

- PR #71 is merged. Its official CBF kickoff correction remains mandatory research chronology evidence; the previous 380-fixture retrospective report is invalid for model selection because same-kickoff look-ahead leakage was confirmed.
- Stage 4 first prospective capture completed successfully on 2026-11-19.
- Stage 5 read-only inventory and materialization preview completed successfully: seven approved competition scopes, seven READY, zero BLOCKED.
- Stage 5 production materialization has **not** been dispatched or verified. Do not describe Stage 5 as complete yet.
- PRs #102, #104, #105 and #106 are merged. PR #106's actual workflow YAML contained an automatic `workflow_run` trigger that contradicted its stated manual-only safety design. This was detected during handover review.
- Corrective PR #118 is merged as `c505844258c77de7d9e376838dc625101c965f1e`. The Stage 5 apply workflow is now manual-dispatch-only and requires the exact typed confirmation. Do not dispatch until a fresh read-only preview has been run and reviewed.
- Production Neon currently reports migrations 001–017 present, including 015 automated identity adjudication and 016–017 immutable prospective snapshot/label migrations. This was independently queried at handover time. The earlier Stage 5 preview artifact was generated before migration 015 was present in its required set and reported only migrations 001–014; it must not be used as proof of the later 015–017 state.
- Stage 6 and Stage 7 workflow/code scaffolding exists in main. Their presence does not mean persistent snapshots or prospective model certification have completed.
- No production predictions are certified or published by these milestones. Value betting remains locked.

## 2. PR #71 — official CBF chronology correction (historical context)

PR #71 was merged on 2026-11-18. Synchronization commit: `7a3ce30163fbf638631b99c0336acbee5b90cb75`; merge commit: `30c5f9640b53c9b5b23445d970fc56b8a82138bd`.

The CBF schedule audit identified provider fixture `2179333578` (São Bernardo–Londrina, CBF match reference 262). The provider kickoff was `20:49:59 BRT`; the official CBF schedule records `19:30 BRT`, corrected research chronology `2026-09-10T22:30:00Z`. The provider timestamp caused the evaluator to place the fixture after another fixture CBF scheduled simultaneously. The earlier fixture's 2–0 result then entered the feature history for the wrongly delayed fixture. This is same-kickoff look-ahead leakage.

Changes made by PR #71:
- Added `backend/data/research/official_kickoff_adjudications.json`.
- Added an evidence-backed chronology adjudication for fixture `2179333578`.
- Preserved raw provider payload, original provider timestamp and source row; only the audited research-time interpretation is corrected.
- Added raw/official timestamp, CBF reference and source URL metadata to the retrospective training report.
- Added fail-closed checks for malformed registry entries, raw timestamp mismatch, missing source rows and incomplete adjudication audit metadata.
- Hardened paired chronological diagnostics to reject older reports without the required chronology basis and audit metadata.
- Added simultaneous-kickoff regression coverage.

**Reason:** prevent a result from a simultaneous fixture being used as pre-match history. The prior 380-fixture retrospective report and derived diagnostics must not be used for model selection. Rebuild them from the unchanged provider corpus after chronology correction. This correction does not establish historical feature availability or PIT certification.

Primary record: `docs/ledger/2026-11-19-pr71-synchronization-update-11.md`.

## 3. Stage 4 — first prospective 5DollarFootballAPI capture

Workflow: [prospective-5dollar-daily-capture.yml](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/prospective-5dollar-daily-capture.yml)  
Run: [44466519770](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44466519770)  
Job: `135365509885` — success  
Commit: `a1cba712b509a0b6c416b7547954ff21c6b8111c`.

Verified result:
- Seven approved competitions completed.
- 65 fixture records captured.
- 14 provider requests and 14/14 timestamped provider responses.
- 72/72 timestamped source observations.
- 190/190 timestamped source-observation sightings.
- 276 provider-response/observation/sighting records linked through required response lineage.
- Zero rejected, quarantined or duplicate records in this capture.
- Competition record counts: Brazil Série A 15; Brazil Série B 2; England Premier League 10; France Ligue 1 9; Germany Bundesliga I 9; Italy Serie A 10; Spain La Liga 10.
- Window covered 2026-11-18 settlement records and upcoming fixtures through 2026-11-27 UTC.
- Schedule is 03:00 UTC / 04:00 WAT. This is evidence capture, not prediction delivery.

This is a successful prospective capture milestone only. It does not prove all historical observations are PIT eligible, certify a model, authorize publication or validate betting value. This capture did not use The Odds API.

## 4. Stage 5 — scope inventory and preview

### 4.1 Initial defect and correction

The first preview rejected all seven approved scopes with `UNEXPECTED_FIXTURE_STATUS_PRESENT`. The planner counted FINISHED and UNKNOWN fixtures but omitted normal SCHEDULED fixtures from its accepted-status total. The database/provider status contract supports seven canonical states: `SCHEDULED`, `LIVE`, `FINISHED`, `POSTPONED`, `CANCELLED`, `ABANDONED`, `UNKNOWN`.

PR #102, [Fix Stage 5 fixture status eligibility gate](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/102), merged as `9b05f93e532d6dcc635b3b4f440a0c3f4b756f6e`.
- Changed fixture-status validation to accept the seven supported states.
- Kept score integrity strict: FINISHED requires scores; every non-FINISHED state must remain scoreless.
- Added regression coverage for the supported status contract and scheduled fixtures.
- No production database writes, provider calls, Odds API calls or migration changes.

**Reason:** scheduled fixtures are expected inventory, not malformed fixture states. The old gate produced a false blocker across all scopes.

PR #104, [Automatically rerun Stage 5 preview after gate changes](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/104), merged as `6f7e0acb5201a9a249cbc57c92ff5bceb8b35235`.
- Kept manual read-only preview dispatch.
- Added automatic read-only preview rerun when canonicalization, its tests or the preview workflow changes on main.
- No writes/provider calls/odds calls.

PR #105, [Fix Stage 5 regression test lint ordering](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/105), merged as `d96de6647754eeddf433a855e90ab7d116240cc3`.
- Corrected Ruff import ordering in the regression test only.
- No behavior change.

### 4.2 Verified read-only preview

Workflow: [Stage 5 identity preview](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/stage-5-identity-preview.yml)  
Run: [44471255485](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44471255485) — completed successfully.  
Job: `135381008811` — success; database/migration check, canonical scope inventory, materialization preview and artifact upload all succeeded.  
Artifact: `14503519963`, `veltrix-stage-5-identity-preview`; SHA-256 `b29df5cbf2f6a96bd9505327388209d6a89dfeb62db99d7c25fbf89004f9b200`.

Artifact independently downloaded and inspected. Materialization preview reports:
- Mode: `DRY_RUN`
- Scope count: 7
- READY: 7
- BLOCKED: 0
- No production writes were performed by this workflow.

Exact scopes:
| Competition | Provider competition ID | Fixture rows | Finished | Unknown | Preview conflicts |
|---|---:|---:|---:|---:|---|
| Brazil Série A | 3118717965 | 131 | 122 | 0 | 0 |
| Brazil Série B | 522514093 | 386 | 380 | 4 | 2 fixture IDs; team alias pair |
| England Premier League | 4160026622 | 111 | 100 | 1 | 2 fixture IDs |
| France Ligue 1 | 3614399544 | 100 | 90 | 1 | 0 |
| Germany Bundesliga I | 686337048 | 101 | 92 | 0 | 0 |
| Italy Serie A | 3405541143 | 106 | 97 | 0 | 0 |
| Spain La Liga | 4212821298 | 110 | 100 | 1 | 0 |

The preview's row counts differ from some earlier inventory snapshots because additional records were present by the time this artifact was generated; use the artifact values above as the evidence for this specific run.

Important caveat: READY means the materialization planner accepted the scope and its provenance/status checks. It is not a statement that all source identities are independently verified, all conflicts disappear, or the resulting historical rows are PIT certified. The artifact specifically records:
- Brazil Série B fixture conflict IDs `2341822348` and `3116209225`.
- Brazil Série B team alias collision `1102583842` / `3808811746`.
- England Premier League fixture conflict IDs `1990703256` and `475377468`.
- Unknown-status rows remain represented in France, Spain and Brazil Série B.
- Inventory-only canonical fixture links are zero before materialization, as expected.

Do not resolve these conflicts by guessing or destructive merge. Keep source IDs and raw evidence. Use the existing automated adjudication evidence ledger and human-confirmed-only canonical merge policy.

### 4.3 PR #106 apply workflow and safety defect found

PR #106, [Add guarded all-scope Stage 5 materialization workflow](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/106), merged as `1574b65eb0be965f4408b3c86dbe6b25e9d79c63`.

It added `.github/workflows/stage-5-identity-apply-all.yml` with:
- Exact seven competition selectors.
- Read-only all-seven preflight before any writes.
- Exact provider/source/competition selectors per apply.
- No provider requests and no Odds API calls.
- Post-apply inventory checks and uploaded per-scope reports.
- Typed confirmation string `APPLY_ALL_SEVEN_APPROVED_SCOPES`.

**Critical code-review finding:** the merged YAML did not actually enforce the PR description's “manual dispatch only” guarantee. It also subscribed to a successful `workflow_run` event from the Stage 5 preview and synthesized the confirmation value for that event. Therefore a future successful preview could automatically trigger production writes without the user manually dispatching the apply workflow. The specific preview run 44471255485 completed before PR #106 was merged, so it did not trigger that newly merged workflow; however, the future-trigger defect remains real until corrected.

### 4.4 PR #118 — merged manual-only production apply correction

A handover safety branch has been created:
`stage-5-manual-apply-safety-and-handover-ledger`.

The branch changes `.github/workflows/stage-5-identity-apply-all.yml` to:
- Remove the `workflow_run` trigger entirely.
- Permit the job only for `workflow_dispatch` with exact typed confirmation `APPLY_ALL_SEVEN_APPROVED_SCOPES`.
- Pass only the user-entered confirmation into the job environment.
- Preserve all existing target database, migration, exact-scope preflight, per-scope apply and post-apply checks.

This is a safety correction, not an authorization to apply. PR #118 merged successfully. Its Vercel preview-feedback check completed successfully with zero unresolved feedback; no backend test workflow was triggered for this workflow/documentation-only change. The merged workflow was fetched from main and independently verified to contain only `workflow_dispatch`, with an exact confirmation condition and no `workflow_run` trigger. No production apply has been dispatched.

## 5. Production database migration state at handover

A read-only Neon query was run against project `young-wind-27772160`, production branch `br-jolly-darkness-balgmi2t`, database `veltrix_ai_analyst`.

The live `public.schema_migrations` table returned 18 rows: the 17 named migration files plus both 008 migrations. The ordered versions include:
- 001–014, as listed in earlier checkpoints.
- `015_automated_identity_adjudication.sql`
- `016_immutable_prospective_feature_snapshots.sql`
- `017_append_only_prospective_snapshot_labels.sql`

This confirms the live migration ledger at query time. It does not establish when/how 015–017 were applied, nor prove Stage 6 snapshot rows exist. The Stage 5 preview artifact from run 44471255485 was created earlier and lists only migrations 001–014; do not conflate that historical artifact with the current live migration ledger.

## 6. Stage 6 and Stage 7 code already present

The main branch contains:
- `.github/workflows/stage-6-daily-snapshot-materialization.yml`
- `.github/workflows/stage-6-persist-prospective-snapshots.yml`
- `.github/workflows/stage-6-prospective-dataset-preview.yml`
- `.github/workflows/stage-7-prospective-research-evaluation.yml`
- `backend/app/validation/certification_gates.py`
- `backend/scripts/apply_prospective_certification_gates.py`
- `backend/tests/test_certification_gates.py`

The Stage 6 persistence workflow rebuilds the prospective dataset read-only, re-audits it, requires eligible rows while explicitly keeping release eligibility false and production/value betting locked, then persists immutable snapshots and labels under an explicit merge-message marker `[PERSIST_STAGE6_SNAPSHOTS]`; it verifies row counts and append-only protection. This workflow must be inspected and its own gate/dispatch conditions understood before it is triggered. Do not assume migration presence equals snapshots persisted.

Stage 7 is a read-only expanding-window prospective evaluation followed by independent production certification gates. The repository has recent commits fixing certification artifact newline handling, Ruff simplification and CLI lint. Stage 7 success must not be inferred from workflow/code presence; inspect its actual runs and artifacts.

## 7. Model, app and release boundaries

- The existing Android UI is to be preserved. Integrate backend predictions into the existing typed API client and screens; do not redesign the dashboard.
- Backend model processing remains server-side.
- App-only release; no Telegram delivery or Telegram dependency.
- Do not publish predictions until PIT, identity, model-artifact, calibration and prospective release gates pass.
- Target is at least 25 eligible predictions per day, but never pad the feed. Publish only eligible fixtures; report a shortfall.
- Core predictions must not depend on bookmaker odds. Value betting remains a separate locked feature.
- Value betting certification remains independent and requires, per market: at least 1,000 walk-forward matches; at least 300 prospective settled selections; at least 90 distinct dates; 98% timestamped odds coverage; positive net ROI with lower 95% ROI confidence bound above zero; and 1X2 beating bookmaker Brier and log loss.
- Protect The Odds API budget; user previously reported 271 monthly credits. Do not make exploratory odds calls.
- 5DollarFootballAPI free-mode personal/non-monetized data collection and internal model training are approved under the recorded scope. Commercial use is not approved.

## 8. Exact next execution sequence

1. PR #118 is merged. Reconfirm its workflow remains `workflow_dispatch` only with the exact typed confirmation; no `workflow_run` path exists.
2. Re-run the Stage 5 read-only preview against current main and the current live migration ledger. Confirm all seven scopes remain READY and inspect updated conflict/review counts.
3. Manually dispatch the Stage 5 apply workflow only after the fresh preview artifact is reviewed. The user must enter `APPLY_ALL_SEVEN_APPROVED_SCOPES`; this manual step is a genuine human authorization boundary.
5. Inspect every per-scope apply JSON, failure summary, post-apply inventory, fixture/team/competition links, identity conflicts, unresolved review cases and artifact. Do not declare Stage 5 complete from workflow conclusion alone.
6. If apply fails for a scope, investigate that scope and retry only after understanding the failure. The materializer is intended to be idempotent; still verify before retry.
7. Reconcile the resulting Stage 5 state with the automated identity adjudication ledger. Automated evidence dispositions do not authorize canonical merges or deletion.
8. Continue Stage 6: inspect preview and daily snapshot workflows, run a read-only prospective dataset audit, then persist only through its explicit protected gate. Verify persisted snapshots, labels and append-only protection.
9. Continue Stage 7: run chronological expanding-window evaluation on persisted PIT snapshots, inspect artifacts and certification-gate outputs. Do not use retrospective leakage-contaminated metrics as certification.
10. Only after all model release gates pass, integrate published predictions into the existing Android UI and conduct physical device verification. Keep Value Bet locked until its separate certification requirements pass.

## 9. Explicit non-actions at this checkpoint

- No Stage 5 production canonical materialization has been performed in this handover.
- No provider requests were made during Stage 5 inventory/preview.
- No Odds API credits were consumed.
- No production prediction publication was enabled.
- No value betting was enabled.
- No Android UI redesign or Telegram integration was performed.
- No historical source payloads or provider IDs were rewritten or deleted.

**Next checkpoint:** fresh Stage 5 read-only preview against the current main branch and live migrations 001–017, followed by explicitly authorized manual apply and post-apply verification.
