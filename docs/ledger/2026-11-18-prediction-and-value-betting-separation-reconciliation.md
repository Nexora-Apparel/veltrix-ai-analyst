# 2026-11-18 — Prediction/value-betting separation and project ledger reconciliation

## Architectural decision — bookmaker odds are for value betting, not core predictions

**Primary objective:** build the strongest independently validated football prediction engine the available data can support. Prediction quality is the project's main objective.

**Secondary objective:** identify value-betting opportunities by comparing independently generated VELTRIX probabilities with bookmaker prices. Bookmaker odds are collected and consumed primarily for this secondary purpose.

The systems must remain logically and operationally separated:

1. The prediction engine generates forecasts from its own eligible football data and statistical/ML models. It must not require bookmaker odds to produce a prediction.
2. Bookmaker odds must not be used as a hidden prior, target, shortcut, feature or override in the core prediction probabilities. Any future exception requires a separately documented decision and leakage-safe validation; the current design excludes this.
3. The value-betting subsystem consumes independently generated model probabilities plus eligible bookmaker prices. It handles implied probabilities, bookmaker-margin removal, expected value, price/market comparison, freshness, source timestamps and qualification.
4. Odds unavailable, stale, invalid, incomplete or outside approved rights/PIT scope means **no value-bet recommendation**; it does not suppress an otherwise eligible football prediction.
5. Odds available but no selection meeting the value threshold means **no value-bet recommendation**; never force a bet.
6. A failed prediction publication gate blocks both prediction publication and downstream value betting. A value-betting gate failure does not invalidate an otherwise valid prediction.
7. Value betting remains disabled until its independent certification requirements are met.

This is a foundational architecture constraint, not a temporary implementation detail. It supersedes any ambiguous wording that could imply bookmakers are required to make predictions or that odds availability controls prediction coverage.

## Prediction-engine quality requirement

The project requires a rigorous, high-performance statistical/ML architecture and independent evidence of predictive performance. It must not be reduced to lightweight heuristics or an LLM-only predictor. Candidate families already implemented/researched include Elo, independent Poisson, Dixon–Coles and attack/defence Poisson, with chronological walk-forward evaluation and fold-contained calibration experiments. Additional feature/model families may be adopted only after data eligibility, identity, leakage, rights and out-of-sample evidence are established.

The target is the highest achievable accuracy supported by evidence; no accuracy percentage is promised in advance. Evaluation must include proper scoring rules (including 1X2 Brier and log loss), calibration diagnostics, meaningful baselines, chronological held-out tests and uncertainty estimates. LLM research/explanations may supplement the system but cannot invent numeric model inputs or override model probabilities.

## Reconciled completed work and evidence

### Foundation, data and controls
- Separate repository, Android client, FastAPI backend and dedicated Neon database established for VELTRIX AI ANALYST; this project remains separate from VELTRIX FOOTBALL 2.0 and other Veltrix projects.
- Architecture/ledger foundations committed (architecture commit `4a996a2`; ledger commit `e6ebb9b`). README remains intentionally untouched for accuracy-improvement detail.
- Neon database `veltrix_ai_analyst` provisioned and verified. Migrations 001–003 and checksums verified. Source approval registered.
- Persistent budget/dry-run controls verified: 34 collection windows/checkpoints, 40-request reservation ceiling, request 41 rejected, replay idempotent, zero fixture rows and zero provider requests in dry-run. Historical import was separately executed only after safeguards.
- 5Dollar Community historical Brazil Serie B collection: 384 provider fixtures, 380 FINISHED and 4 UNKNOWN; 34 windows and 34 requests in the recorded collection interval. Canonicalization produced 384 canonical fixtures, 21 provider team IDs, 1 competition, 384 source links and 28 review cases/events. Identity/duplicate/competition review remains unresolved; no human review events recorded. Do not treat the imported retrospective data as PIT-certified.
- All 384 source observations/sightings in that audit lacked source publication and local availability timestamps; they were RETRIEVED_AT_ONLY. No PIT feature observations were admitted. Kickoff time and HTTP Date are not substitutes for source publication/availability time.
- Full fixture reconciliation against the relevant official competition records remains outstanding; America MG alias and duplicate/identity cases remain unresolved.

### Model core and retrospective research
- PR #23 merged the core typed contracts, strict PIT admission, Elo, independent Poisson, Dixon–Coles and chronological walk-forward validation.
- PR #29 added retrospective training/evaluation over 380 FINISHED fixtures using provider-local team IDs without alias merging.
- PR #31 fixed ridge regularization and added a league baseline.
- Immutable v1 artifact: `v1-5790da5427a7029b9267778728386b8d`.
- Nested-tuned v2 artifact: `v2-5790da5427a7029b9267778728386b8d`; 380 training fixtures, 20 provider-local teams, 34 inner chronological folds/340 predictions; PIT false.
- Nested v2 vs league baseline on 305 held-out fixtures / 12 folds: Brier 0.612446105989228 vs 0.6420315330733214; log loss 1.0215836752228307 vs 1.0633200834823107. The fold-block bootstrap favoured v2 against that baseline, but this remains exploratory retrospective evidence from one competition/season.
- Matched fixed-v1 vs nested-v2 on the same 305 held-out fixtures: v1 Brier 0.6081835337 and log loss 1.0153185492; v2 Brier 0.6124461060 and log loss 1.0215836752. Paired fold-block intervals favoured fixed v1 on both primary metrics.
- Fold-contained temperature scaling worsened Brier/log loss for both models; it must not be enabled by default. Preserve v2 as an immutable comparator; fixed v1 remains the retrospective benchmark candidate.
- Neither model is PIT-certified, production-certified or approved for public prediction publication. These tests establish engineering/evaluation behaviour and retrospective comparative evidence, not proven live accuracy.

### Odds provider qualification — value-betting research only
- 5Dollar Community account was verified; existing account/credentials are reused. Community tier supports the bounded fixture snapshot probe; full odds tick history is Ultra-only and must not be called under the current tier.
- Prior one-fixture 5Dollar probe for fixture `1194891794` returned HTTP 200 and Bet365 1X2 opening prices 4.10 / 3.25 / 1.90, with `opened_at=2026-11-09T13:15:09Z`; retrieved on 2026-11-18. This proves endpoint/schema access only, not historical PIT availability or CLV.
- PR #47 implemented strict event-to-fixture matching; PR #48 added cross-provider catalogue qualification; PR #49 added strict event-specific h2h response parsing; PR #51 authorized a single event-specific h2h request only after complete catalogues and exactly one unique match; PR #52 records actual quota cost from response headers; PR #54 added deterministic single-fixture selection. PR #54 merged as `21e897e3edf5894c83450cb1c05a5577e5df27b0`.
- Qualification workflow run [44228137046](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44228137046), job 134546276121, completed successfully. Artifact ID `14393503288`.
- The Odds API events catalogue and 5Dollar scheduled-fixture catalogue both returned HTTP 200 and were complete (20 future events and 20 future fixtures); four exact unique fixture matches were found. Deterministic selection chose Aston Villa vs Sunderland, fixture ID `4042864659`, Odds API event ID `b8d6ab6ecc8bb356c6335d3f417d0ecf`, kickoff `2026-11-21T15:00:00Z`, exact home/away orientation and zero kickoff delta.
- One UK-region h2h market request returned HTTP 200 with 21 bookmakers and 63 valid timestamped HOME/DRAW/AWAY quotes. No incomplete bookmakers, invalid quotes or missing timestamps were rejected. No retries, pagination or DB writes.
- Odds API quota accounting: events catalogue cost 0; h2h request cost 1. Last confirmed balance after the run was 270 monthly credits remaining (quota used 230). This is a historical last-confirmed observation, not a live balance guarantee. Do not spend additional credits for the same comparison without a specific need.
- 5Dollar catalogue request count was 1; last observed Community rate-limit remaining was 299/300.
- **Outstanding comparison gap:** workflow run 44228137046 did not retrieve a matching 5Dollar Bet365 odds snapshot for fixture `4042864659`. Therefore there is no cross-provider same-fixture price comparison yet. The 5Dollar snapshot for fixture `1194891794` is a different fixture and cannot substitute.
- The qualification result demonstrates provider access, exact fixture matching and timestamped Odds API quote availability. It does not establish broad timestamp coverage, historical PIT eligibility, price freshness at prediction cutoff, CLV, profitability, value-bet qualification or permission for unapproved uses.

### Prospective capture and release gates
- Prospective capture contract is documented in [2026-11-18-prospective-odds-capture-contract.md](2026-11-18-prospective-odds-capture-contract.md). It keeps request start, retrieval, provider response date, source tick, fixture kickoff and prediction cutoff distinct. A source tick before cutoff is not enough if local retrieval occurred after cutoff.
- Initial capture envelope is manual-only, one fixture per dispatch, at most one HTTP request per fixture, no retries/pagination/history/bulk odds endpoints, no DB writes until typed contracts/tests pass.
- The matching 5Dollar snapshot for fixture `4042864659` remains the next narrowly scoped provider task. Use one fixture-specific 5Dollar request only, subject to the recorded Community quota cap; do not repeat the Odds API request. If the provider lacks the corresponding Bet365 market/timestamp, record missing coverage rather than infer or fabricate it.
- No odds DB writer, recurring collection, model odds features, CLV claim, paper ledger, value-bet activation, production prediction endpoint, public forecasts, model promotion or Android/backend prediction integration is authorized yet.
- Android dashboard work remains deferred. Existing dashboard commit `c23dc52f8c267236aa1ccf0c9234ab85515054aa` is pending later runtime testing; integrate typed backend responses only after real prediction endpoints exist.

## Current next actions
1. Preserve the prediction/value-betting separation in code, schemas, tests, UI and future documentation.
2. Retrieve one matching 5Dollar odds snapshot for fixture `4042864659` (single request, no retries) and audit bookmaker mapping, market/selection normalization, decimal prices, all timestamps, response hash and fixture identity.
3. Implement and test pure typed prospective capture contracts and strict PIT/idempotency/rights boundaries before any DB writer.
4. Continue resolving fixture/team identity and source provenance before promoting retrospective data into PIT-eligible training features.
5. Continue model research with leakage-safe chronological evaluation and stronger multi-competition data; do not promote a model based on retrospective one-league results alone.
6. Keep all prediction publication and value-betting release gates closed until their separate evidence requirements are met.

## Ledger integrity note
This entry reconciles the architectural decision and material completed work known through 2026-11-18. It distinguishes completed implementation, retrospective research, provider-access evidence, outstanding blockers and prohibited activation. It does not claim that every historical chat action has been independently reverified against GitHub in this entry.
