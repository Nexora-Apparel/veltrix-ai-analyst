# 2026-11-20 — Stage 8B retrospective rebuild passed

## Execution evidence

- CI run: [44712955417](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44712955417), job 136209024795, branch `stage-8b-statistics-ci-release`, head `e61791463e142a4afceaab363537ba853f37a4cb`.
- CI conclusion: success. Backend tests, Ruff lint, Android debug build and APK upload all completed successfully.
- APK artifact ID: `14618615613`; size 16,448,828 bytes; artifact SHA-256 `268da91198a0dba132cf0f7bed92d4e9a22acb1a200f323d31891a8a3d3dff96`.
- Research rebuild: [44713600712](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44713600712), job 136211231020, same branch and head. Every step completed successfully: read-only historical import validator, statistics-aware feature dataset build, retrospective report rebuild, paired chronological diagnostics and all three artifact uploads.

## Corrected source accounting

The generated report confirms the expected accounting invariant:

| Classification | Rows |
|---|---:|
| Total source rows | 386 |
| FINISHED with both scores | 380 |
| UNKNOWN without scores | 4 |
| SCHEDULED without scores | 2 |
| INVALID | 0 |

Only the 380 FINISHED rows were used as retrospective labels. The two valid upcoming fixtures were excluded as scheduled/unlabelled, not misclassified as malformed records.

## Retrospective model report

- Report artifact: `corrected-retrospective-research-report`, artifact ID `14618990915`, 38,510 bytes; ZIP digest `sha256:63a157e52f98651e06c7bff7987f829568c8279e147ff2dea24ec1131d551c66`.
- Internal report SHA-256: `14a69cc1d0b3b786d4a11808079b43ab0d3ffa97581e1136a3881e5cb8813ad5`.
- Dataset type: `RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED`; one competition, 20 teams, 380 fixtures, 2026-03-21 through 2026-11-14.
- 1X2 full-corpus prequential scores:
  - Elo: Brier 0.6333636621; log loss 1.0511312957.
  - Poisson: Brier 0.6305494554; log loss 1.0480440262.
  - Ensemble: Brier 0.6293348931; log loss 1.0458888491.
- Ensemble has the lowest point estimate in this retrospective comparison, but paired moving-block bootstrap intervals for all pairwise Brier and log-loss differences include zero. These results do not establish a statistically reliable winner. The diagnostics explicitly prohibit pooling this full-corpus prequential sample with the separate nested chronological walk-forward sample.
- No bookmaker odds were used. The report therefore does not demonstrate improvement over bookmaker Brier/log loss, nor does it certify any betting market or ROI.

## Statistics-aware feature dataset

- Artifact: `statistics-aware-retrospective-feature-dataset`, artifact ID `14618123576`, 653,709 bytes; ZIP digest `sha256:c9b9bdabd0c8a96eaac92c52de723aa2b635d30ca34f26f36995d5698f4de6c2`.
- Dataset SHA-256: `fd805256d0015f08e05f4a312d065fa8f8c00170227ac08e37ac10d11be7bf55`.
- 1,576 rows across seven competitions; 40 statistics-derived home/away feature fields.
- Non-null feature-cell coverage: home perspective 29,960/31,520 (95.05%); away perspective 30,060/31,520 (95.37%). At least one home statistics mean exists in 1,498 rows; at least one away statistics mean exists in 1,503 rows.
- All 1,576 rows are tagged `RETROSPECTIVE_EVENT_TIME_RECONSTRUCTION`; all have `source_available_before_target_kickoff=false`. Dataset-level `point_in_time_certifiable=false`, `validation_eligible=false`; every row is certification-ineligible. Current rights status is APPROVED, but retrospective rights approval does not establish historical pre-kickoff availability.
- These features are suitable for exploratory retrospective research only. They must not be described as PIT-qualified, used for prospective certification, or promoted into production inference based on this run.

## Paired diagnostics

- Artifact: `corrected-paired-chronological-diagnostics`, artifact ID `14619310095`, 3,841 bytes; ZIP digest `sha256:a474c5d3096f374e9d04470c339287ef48b07e7b70c3fff33b8c8b9973758101`.
- 380 fixtures; four chronological periods; 2,000 paired moving-block bootstrap resamples, block size 20 fixtures.
- The 95% intervals include zero for Elo-vs-ensemble, Elo-vs-Poisson and Poisson-vs-ensemble for both Brier and log loss. Descriptive retrospective comparison only; not PIT certification.

## Scope and safety boundaries

- The rebuild reused existing historical observations. No repeat collection or new 5DollarFootballAPI requests were required; no Odds API credits were spent.
- Import validation and dataset materialization were read-only. No production database writes, deployment, PR merge or production publication occurred.
- PR #123 remains open/unmerged at head `e61791463e142a4afceaab363537ba853f37a4cb`.
- Stage 7 prospective certification, production inference/publication and value betting remain locked. This successful CI/research run is engineering/research evidence only.

## Next actions

1. Keep the statistics-aware retrospective dataset isolated from prospective certification datasets.
2. Use it only for exploratory feature diagnostics and model research, with the non-PIT boundary carried into every report.
3. Build/evaluate feature effects on prospectively observed pre-kickoff snapshots joined only to strictly post-kickoff labels; accumulate sufficient distinct dates and settled outcomes.
4. Continue Stage 8B/8C integration and reliability calibration. Do not merge PR #123 solely because these workflows passed; review the complete PR and remaining Stage 8 exit criteria first.
5. Preserve existing Android UI; integrate only after a certified immutable artifact and publisher exist.


## PR integration status — post-rebuild check

- PR #123 remains open and unmerged. GitHub reports `mergeable=false`.
- Branch comparison against `main`: candidate is 119 commits ahead and 3 commits behind; the branches diverged from merge base `7039615d51a30609a67a944c050bd8b31ce20bce`.
- The three main-only commits add the default-branch historical evidence preflight workflow, enforce a read-only transaction in that preflight, and expose the bounded historical backfill workflow. Both main and the candidate branch contain different versions of `.github/workflows/historical-feature-evidence-backfill.yml`; the candidate must preserve its verified run behavior while incorporating the later default-branch safety refinements. The candidate also needs the main-only preflight workflow.
- Do not merge while GitHub reports non-mergeable. Next integration task is a deliberate workflow reconciliation against those three main commits, followed by fresh CI on the resulting exact head. The already successful CI/research runs remain valid evidence for their original tested head only; documentation-only commits and any subsequent workflow reconciliation are not thereby CI-verified.
