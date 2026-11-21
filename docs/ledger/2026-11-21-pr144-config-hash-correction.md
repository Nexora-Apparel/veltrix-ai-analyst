# 2026-11-21 — PR #144 v3.2 configuration fingerprint correction

## Scope and correction

- One corrective PR; no production, database, provider, Odds API, Telegram, scheduler, quarantine, feed, or lock changes.
- Frozen schema: `veltrix-shrinkage-selection-v3.2`.
- Canonical config: `docs/research/shrinkage-selection-v3.json` (not edited).
- Correct canonical SHA-256: `d087f3d641eccf8b81a6717d691db1edab0fd5402119182d18e01e56eadd176a`.
- Canonicalization exactly matches the evaluator: Python `json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`, then one trailing newline, UTF-8, SHA-256.
- The workflow's input default and immutable-input hardcoded comparison are both updated to the corrected hash.
- CI test computes the committed config hash and compares it with the workflow default, workflow hardcoded gate, and this preregistration record.

## Diff investigation and freeze integrity

The config was fetched at `692e118` and `82d0f42f0cfda19442887495ef6132d22a9a187b`. Both have identical Git blob SHA `eb179fc5c45fa35c86c945bb3b673d7b7b73bcca` and identical 4,824-byte content. Exact JSON diff between those references: **no changes**.

The previous recorded value `90aea1d84cbe2301f71f5e3d6910d913ae2d1b79c7658319e5cf3ee0817df62a` is not the canonical hash of that committed file. The evidence supports a stale recorded fingerprint; it does not support a JSON edit between the two specified commits. The earlier origin of the stale value remains unestablished.

No evaluation results existed at correction time; no candidate had been selected. The config JSON is not changed. Grid, selection, convergence, historical availability, and admission rules remain unchanged.

## Mechanical source preflight

| Assertion / input | Observed value | Result |
|---|---|---|
| Evaluation commit supplied to workflow | Must be exact merged main SHA; PR will supply updated SHA after merge | Pending owner merge |
| Dataset run ID | `44873016040` | Pass |
| Dataset artifact ID / name | `14694463354` / `veltrix-stage6-daily-materialization-audit` | Pass |
| Dataset artifact expiry | `false`; expires 2027-02-19 | Pass |
| Dataset archive SHA-256 | `3a2ebfb7dd94899bc1cf5000bb365c440753afcfa474869a733bbeeda0a1ad81` | Pass |
| Dataset ZIP integrity / file layout | ZIP test passed; exactly `prospective-dataset.json` | Pass |
| Dataset embedded SHA-256 | `80148b3f0f42e70d94391d9283c42f35b5b92e1631a9a1cb7baee899373dad0c` | Pass |
| Forecast run ID | `44873166128` | Pass |
| Forecast artifact ID / name | `14694089682` / `veltrix-prospective-shadow-forecasts` | Pass |
| Forecast artifact expiry | `false`; expires 2026-12-21 | Pass |
| Forecast archive SHA-256 | `44164d6e9ead148b6fa0e663f81bde18ad5f75e839143e408a2ecce98cc7f16f` | Pass |
| Forecast ZIP integrity / file layout | ZIP test passed; exactly `prospective-shadow-forecasts.json` | Pass |
| Forecast embedded dataset SHA | Matches pinned dataset SHA above | Pass |
| Training rows | 996 | Pass |
| Forecast predictions | 25 | Pass |
| Recomputed training_data_sha256 | `d70ee34940c8fc6681f3cd5751d4fdcc2e876b307fe388d9f3a792c73e34b262` | Pass |
| Forecast training_data_sha256 | Same as recomputed value | Pass |
| Per-prediction training hashes | All 25 match | Pass |
| Training field contract | All 996 rows contain evaluator-required fixture, competition, team, kickoff, and nested goal-label fields; workflow preflight invokes evaluator `_result` on every row | Pass |
| Timezone-aware timestamps | All 996 kickoff and label-observation timestamps parse as timezone-aware | Pass |
| Config schema | `veltrix-shrinkage-selection-v3.2` | Pass |
| Canonical config SHA-256 | `d087f3d641eccf8b81a6717d691db1edab0fd5402119182d18e01e56eadd176a` | Pass |
| Grid | 10 k values × 3 half-lives × 4 blend weights = 120 | Pass |
| Workflow immutable inputs | All six pinned source constants match the recorded artifact identities/hashes; evaluation SHA is validated as 40 lowercase hex and main ancestry | Pass by source inspection; runtime ancestry remains workflow-gated |
| Production/admission controls | Retrospective-only; no PIT certification or promotion | Unchanged |

## CI and merge status

- Added CI test binding the canonical config hash to the workflow default, workflow hardcoded validation, and preregistration document.
- Added exact 10 × 3 × 4 grid-size test.
- Added evaluator field-contract test.
- Workflow artifact preflight now validates schema/grid cardinality and calls the evaluator's real row conversion on all 996 pinned training rows before evaluation.
- Exact-head CI is required before this PR is reported ready for owner merge.
- No evaluation workflow was dispatched. This PR only repairs fingerprint integrity and preflight safeguards.
