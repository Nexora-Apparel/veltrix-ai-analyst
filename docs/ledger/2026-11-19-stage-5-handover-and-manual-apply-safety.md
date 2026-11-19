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
- Stage 5 production materialization subsequently ran through pre-PR-118 automatic workflow triggers and was independently verified in run 44494508790. All 1,063 fixture source links across seven scopes are present; five fixture identity conflicts and one team identity conflict remain explicitly recorded, plus two global Brazil Série B review restrictions. See Section 10 for the correction and exact counts.
- PRs #102, #104, #105 and #106 are merged. PR #106's actual workflow YAML contained an automatic `workflow_run` trigger that contradicted its stated manual-only safety design. This was detected during handover review.
- Corrective PR #118 is merged as `c505844258c77de7d9e376838dc625101c965f1e`. The Stage 5 apply workflow is now manual-dispatch-only and requires the exact typed confirmation. The previous automatic apply runs occurred before this safety correction; future applies require a manual dispatch.
- Production Neon currently reports migrations 001–017 present, including 015 automated identity adjudication and 016–017 immutable prospective snapshot/label migrations. This was independently queried at handover time. The earlier Stage 5 preview artifact was generated before migration 015 was present in its required set and reported only migrations 001–014; it must not be used as proof of the later 015–017 state.
- Stage 6 has persisted and verified 59 immutable prospective feature snapshots, with zero settled labels so far. Stage 7 evaluation has run but is correctly blocked: zero settled labels, zero expanding folds, zero evaluated fixtures, and production certification remains locked.
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

This is a safety correction, not an authorization to apply. PR #118 merged successfully. Its Vercel preview-feedback check completed successfully with zero unresolved feedback; no backend test workflow was triggered for this workflow/documentation-only change. The merged workflow was fetched from main and independently verified to contain only `workflow_dispatch`, with an exact confirmation condition and no `workflow_run` trigger. Historical apply runs using the earlier automatic trigger were discovered afterward and are fully reconciled in Section 10.

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


---

## 10. Post-handover reconciliation — later workflow runs discovered (2026-11-19)

**This section supersedes earlier statements in this ledger that Stage 5 production materialization had not yet run.** The earlier handover was prepared from a partial view of the workflow history. A subsequent full Actions run inventory showed that the pre-PR-118 automatic `workflow_run` trigger had already started Stage 5 apply jobs. The latest successful run and its uploaded artifact were inspected.

### 10.1 Stage 5 production apply did run before PR #118

Relevant successful runs discovered from the repository Actions history:

| Run | Event | Result | Interpretation |
|---|---|---|---|
| [44472105659](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44472105659) | workflow_dispatch | success | Earlier manually dispatched apply |
| [44476589584](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44476589584) | workflow_run | success | Automatic apply before safety correction |
| [44477076919](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44477076919) | workflow_run | success | Automatic repeat |
| [44491882486](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44491882486) | workflow_run | success | Automatic repeat |
| [44494508790](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44494508790) | workflow_run | success | Latest successful apply before PR #118 |

The latest run #44494508790 was triggered by `workflow_run`, not by a fresh manual dispatch. Its log explicitly shows the workflow synthesized `CONFIRMATION=APPLY_ALL_SEVEN_APPROVED_SCOPES` for the automatic event. This confirms the defect PR #118 corrected was exercised. Do not describe those automatic apply executions as user-manually authorized.

The later repeated runs were idempotent: their reports show zero new fixtures/teams/competitions created and all existing scoped fixture rows reused. No provider requests were made.

### 10.2 Latest Stage 5 apply artifact independently inspected

Run: [44494508790](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44494508790)  
Job: `135458165390` — success  
Artifact: `14514996120`, `veltrix-stage-5-identity-apply-all`  
Artifact SHA-256: inspect from downloaded ZIP if regenerated; the repository Actions artifact is the primary evidence.

All seven exact scopes passed the read-only preflight and each per-scope apply report returned `APPLIED`. The job then passed its post-apply inventory/linkage verification. No provider requests were made.

| Competition ID | Fixture rows | Linked rows | Verified identities | Identity conflicts | Review required |
|---|---:|---:|---:|---:|---:|
| Brazil Série A — 3118717965 | 131 | 131 | 131 | 0 | 0 |
| Brazil Série B — 522514093 | 386 | 386 | 382 | 4 | 0 |
| England Premier League — 4160026622 | 111 | 111 | 110 | 1 | 0 |
| France Ligue 1 — 3614399544 | 100 | 100 | 100 | 0 | 0 |
| Germany Bundesliga I — 686337048 | 90 | 90 | 90 | 0 | 0 |
| Italy Serie A — 3405541143 | 120 | 120 | 120 | 0 | 0 |
| Spain La Liga — 4212821298 | 125 | 125 | 125 | 0 | 0 |
| **Total** | **1,063** | **1,063** | **1,058** | **5** | **0** |

Additional post-apply verification:
- All seven source competition links exist.
- All catalogued team source links exist.
- Brazil Série B has one team identity conflict, zero team review-required links.
- Fixture conflicts remain explicitly visible: four in Brazil Série B and one in England Premier League.
- No unresolved linked review cases remain.
- Two unlinked global review cases remain recorded:
  - `BRAZIL_SERIE_B_RUN_3_PIT_TIMESTAMP_GAP`: `AUTOMATED_DEFERRED`; keep 374 observations out of pre-match features until source publication/availability timestamps are verified.
  - `BRAZIL_SERIE_B_RUN_3_COVERAGE_2026`: `AUTOMATED_CONFIRMED`; reconcile all 370 finished rows to CBF rounds 1–37 before certifying coverage.
- The final inventory reported no missing required migrations.

**Corrected Stage 5 status:** production source-local/canonical linkage materialization for all seven approved scopes has been executed and independently verified by the successful apply artifact. Stage 5 is complete as a materialization milestone, with five fixture identity conflicts, one team identity conflict and the two global Brazil Série B review cases retained as explicit unresolved/restricted evidence. It is not a claim that every fixture identity is verified or that historical PIT is certified.

PR #118 remains important: it prevents future automatic apply executions. Its merge occurred after the runs above. The merged workflow on main now accepts only manual `workflow_dispatch` with exact typed confirmation. The earlier automatic runs are historical and cannot be retroactively converted into manual approvals.

### 10.3 Stage 6 — persistent prospective snapshots have been written and verified

Successful run: [44492260988](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44492260988)  
Job: `135450607753` — success  
Artifact: `14513342300`, `veltrix-stage6-persisted-snapshot-audit`.

The artifact and job log show:
- Dataset status: `READY_FOR_RESEARCH`.
- Eligible prospective rows: 59.
- Distinct competitions: 7.
- Distinct kickoff dates: 6.
- Feature-lineage records: 113.
- Invalid system-observed sightings: 0.
- Settled label rows: 0.
- Unsettled rows: 59.
- Dataset SHA-256: `60cf113db9ea055e5cbbd72c7dbbb0a26cbbad2dca2f5ca76e9eba2a41fbc91c`.
- Persistence verification: 59 snapshots, 59 distinct fixtures, 0 settled labels.
- Release eligibility: false; production promotion: LOCKED; value betting: LOCKED.

A later daily materialization run [44494939469](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44494939469) also succeeded. It rebuilt the same dataset and reported 59 snapshots verified, zero labels, with all 59 existing snapshots unchanged. This confirms idempotent daily persistence for the current dataset.

A direct read-only Neon query independently returned:
- `prospective_feature_snapshots`: 59 rows, 59 distinct canonical fixtures.
- `prospective_feature_snapshot_labels`: 0 rows.

**Corrected Stage 6 status:** initial immutable prospective snapshot persistence is complete and verified for 59 fixtures. Outcome labels have not yet accumulated. Continue daily capture/materialization so fixtures settle and append-only label records are recorded. This is not a model-training or certification milestone.

### 10.4 Stage 7 — evaluation executed, correctly blocked for insufficient settled data

Latest inspected run: [44497523416](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44497523416)  
Job: `135468422888` — workflow success  
Artifact: `14515921681`, `veltrix-stage7-prospective-research-evaluation`.

The workflow succeeded technically because the evaluation and certification-gate scripts completed and uploaded their reports. The report outcome is not a certification pass:

- Evaluation status: `INSUFFICIENT_PROSPECTIVE_DATA`.
- Prospective rows: 59.
- Settled labels: 0.
- Fixtures evaluated: 0.
- Expanding folds: 0.
- Distinct settled kickoff dates: 0 (requirement 90).
- Settled prospective fixtures: 0 (requirement 300).
- Walk-forward fixtures per market: 0 (requirement 1,000 each).
- 1X2 bookmaker Brier/log-loss comparison: not evaluated.
- Timestamped odds coverage and ROI confidence: not evaluated; value betting remains locked.
- Production certification: `BLOCKED_INSUFFICIENT_OR_UNCERTIFIED_EVIDENCE`.
- Production promotion: `LOCKED`.
- Release eligible: false.

This is the correct fail-closed outcome. Do not label Stage 7 certified or production-ready because the GitHub workflow itself has a green conclusion.

### 10.5 Current stage table (supersedes earlier table)

| Stage | Correct status | Evidence / remaining work |
|---|---|---|
| 1. Canonical scope inventory | Complete | PR #99 |
| 2. Approved-scope materializer | Complete | PR #100 |
| 3. Production migrations | Applied through 017 | Live Neon migration ledger |
| 4. Prospective daily capture | First run verified; continue daily | Run #44466519770 and subsequent capture chain |
| 5. Seven-scope canonical linkage materialization | **Applied and verified with retained conflicts/review restrictions** | Run #44494508790, artifact #14514996120 |
| 6. Immutable prospective snapshots | **59 persisted and verified; labels pending** | Runs #44492260988 and #44494939469 |
| 7. Prospective model evaluation/certification | **Executed; certification blocked by zero settled labels** | Run #44497523416, artifact #14515921681 |
| 8. Prediction publication | Locked | Requires prospective labels, validated model and all release gates |
| 9. Android physical runtime verification | Pending | After certified prediction API integration |

### 10.6 Next execution sequence — revised

1. Preserve the corrected Stage 5 state; do not rerun bulk materialization unnecessarily. Any future re-run must be deliberate, manually dispatched and idempotency-verified.
2. Keep the five fixture conflicts and one team conflict explicitly quarantined from any identity-dependent feature/prediction path. Never auto-merge them merely because Stage 5 completed.
3. Keep the 374 Brazil Série B observations with the PIT timestamp gap excluded from pre-match features. Reconcile the 370 finished rows against official CBF rounds before certifying coverage.
4. Continue the approved daily 5DollarFootballAPI capture and Stage 6 daily snapshot/label materialization. Monitor the 59 existing snapshots and append settled labels only when actual source-observed result evidence becomes available.
5. Each time new labels arrive, run chronological expanding-window evaluation. Do not count 59 snapshots as 59 settled evaluation examples.
6. Revisit model certification only when the strict sample and date gates can actually be evaluated. Keep production publication and value betting locked.
7. Once certified, integrate the prediction pipeline into the existing Android screens without redesign and perform physical-device verification.

**No new provider calls or Odds API credits were used for this reconciliation.** Stage 5 writes happened in the earlier automatic apply runs documented above; Stage 6 persisted the 59 prospective snapshots. No predictions were published and no value betting was enabled.
