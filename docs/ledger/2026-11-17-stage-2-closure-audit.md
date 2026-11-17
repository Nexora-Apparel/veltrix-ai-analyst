# VELTRIX AI ANALYST — Stage 2 closure audit

**Audit date:** 2026-11-17  
**Scope:** Brazil Série B 2026 historical source qualification, fixture coverage, identity integrity, production provenance and point-in-time eligibility.  
**Database:** `veltrix_ai_analyst` (Neon project `young-wind-27772160`)  
**Provider:** 5DollarFootballAPI, competition `522514093`, source `5dollarfootballapi`

## Executive status

**Stage 2 is close-ready but not fully closed.** The historical foundation, migrations, provenance audit, first-37-round matchup reconciliation and Round 38 provider import are verified. The ten new provider fixtures still require the separate guarded canonical incremental workflow to be manually dispatched and independently verified. No credentials are exposed and no direct SQL fixture inserts will be used to bypass the provenance pipeline.

## 1. Production database and migration state

- Migrations 001–009 are applied; migration 009 was independently read-verified in production.
- Canonical layer before Round 38 incremental materialization: 21 teams, one competition, 374 canonical fixtures.
- Source links before Round 38 incremental materialization: 21 team links, one competition link, 374 fixture-source links.
- Current provider scope after import run 5: 384 fixtures; ten are awaiting canonical source links. Read-only provenance checks confirm the existing 374 fixture links, all 21 team links and the competition link match the earliest matching source sightings.
- Review queue: 28 cases and 28 automated recommendation events.
- Effective active aliases: zero. Effective duplicate exclusions: zero.
- PIT feature observations: zero.
- Team/competition/source links remain in review-required/source-row-only states. This is intentional; no automated recommendation was promoted to a human decision.

Historical import run 3 is recorded as COMPLETED:
- Boundary: `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`.
- Requests: 34 of 40 reserved budget.
- Rows seen/inserted: 374.
- FINISHED with scores: 370.
- UNKNOWN: 4.
- Rejected/quarantined rows: zero.

## 2. Fixture coverage reconciliation

Independent read-only production query confirms:
- 20 distinct provider team IDs across the 370 FINISHED fixtures.
- Every team has exactly 37 appearances.
- 370 distinct ordered home/away pairings; no repeated ordered pairing.
- Of the 190 unordered club pairs, 180 have both home/away directions represented and 10 have only one direction represented.
- The 10 missing directed pairings are exactly the official CBF Round 38 schedule:

| Home | Away |
|---|---|
| América MG | Avaí |
| Atlético-GO | Cuiabá |
| CRB | Ceará |
| Criciúma | Novorizontino |
| Fortaleza | Vila Nova |
| Juventude | Botafogo-SP |
| Londrina | Náutico |
| Ponte Preta | Operário-PR |
| São Bernardo | Athletic |
| Sport | Goiás |

This is a strong structural reconciliation: the 370 imported FINISHED fixtures cover the 37 completed rounds' matchup set, and the only 10 missing directed pairings correspond exactly to the official final-round schedule. It is not a claim that every historical score has been independently compared against an individual CBF match page.

Official CBF references:
- [2026 detailed competition table and Round 38 schedule](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026?doc=Tabela+Detalhada)
- [CBF detailed schedule for rounds 35–38](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro-serie-b/a/cbf-divulga-tabela-detalhadaa-da-reta-final-da-serie-b)
- [CBF official Round 38 results and champion report, 14 Nov 2026](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro-serie-b/a/novorizontino-e-campeao-da-serie-b)

The CBF report confirms the ten Round 38 results:
- Londrina 2–1 Náutico
- Ponte Preta 0–2 Operário-PR
- São Bernardo 2–2 Athletic
- América-MG 0–2 Avaí
- Fortaleza 1–0 Vila Nova
- Atlético-GO 1–0 Cuiabá
- Criciúma 0–1 Novorizontino
- Sport 3–0 Goiás
- CRB 1–1 Ceará
- Juventude 2–0 Botafogo-SP

Some matches were rescheduled to 11 and 12 November; the remaining fixtures were played 14 November. These results are official external reconciliation evidence only; they have **not** been inserted into the production database because they were not captured through the approved provider ingestion/provenance pipeline.

## 3. UNKNOWN rows and identity review

Four UNKNOWN provider rows remain scoreless and have strong evidence of being stale/duplicate counterparts to FINISHED rows:
- `2341822348` ↔ `3116209225`: Goiás 3–1 América MG.
- `2336910968` ↔ `1587564237`: Fortaleza 3–0 Londrina.
- `933498248` ↔ `236839304`: Fortaleza 1–0 Botafogo-SP.
- `1988139832` ↔ `553958702`: Ceará 2–1 Londrina.

The America MG / América Mineiro provider-ID collision remains a human review case. Automated review recommendations are not approvals. No alias merge, fixture reparenting, source-row rewrite or duplicate exclusion is activated.

## 4. Rights and point-in-time eligibility

### 5DollarFootballAPI
The provider's public documentation permits using, displaying and caching data in the customer's own products and models, while prohibiting raw-feed resale/redistribution. Community public-facing use requires visible attribution. The production approval is scoped to the observed account-entitled competitions.

The API exposes kickoff/event timestamps and describes continuously updated results/statistics and tick-stored odds. The inspected fixture contract does not expose a verifiable source publication timestamp or source-availability timestamp for historical result/statistic fields. The current production observations are all retrieved-at-only:
- 374 source observations; zero PIT-certifiable.
- 374 sightings; zero PIT-certifiable.
- No pre-match feature observation has been promoted.

Therefore, settled scores can serve as outcome labels subject to identity/rights controls, but these rows cannot be used as pre-match features or training inputs that require a proven point-in-time cutoff. Kickoff time is not publication time.

### AI Midas
The pinned Brazil Série B snapshot remains non-commercial only, with 368 descriptive candidate matches after quarantining one inconsistent match. It has no verified source publication/availability timestamp and is not PIT-eligible. It must not be represented as a timestamp-qualified feature source or commercial feed.

## 5. Final bounded import — manual blocker

PR #20 merged as `69f91a99b162804fa6a1baa8cd35d9cdc3388488` and the controlled Round 38 import has now completed in workflow run [#44107179999](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44107179999). Import run 5 used two of four permitted requests and inserted ten fixtures with zero duplicates, rejects or quarantines. Provider scope is now 384 fixtures: 380 FINISHED with scores and four UNKNOWN.

PR #22 adds the separate guarded canonical incremental path and merged as `1f45c1b3547d77d3127b84a111e3611e63efeb72`. CI run [#44116261032](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44116261032) passed 122 backend tests, Ruff and Android debug build. Read-only Neon checks confirm the existing 374 fixture mappings and all 22 team/competition mappings match the materializer's expected provenance; exactly ten fixture source links remain absent. The new runner is intentionally a full-scope reconciliation: reuse 374 mappings, create ten, preserve the 28-case review queue, and retain all REVIEW_REQUIRED/SOURCE_ROW_ONLY states.

**Manual execution blocker:** this session has no GitHub Actions workflow-dispatch operation. Open [Materialize Round 38 canonical fixtures](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/materialize-round38-canonical-incremental.yml) and dispatch with `confirm_materialization=MATERIALIZE_BRAZIL_SERIE_B_RUN_5_INCREMENTAL`. Then independently verify 384 canonical fixtures and source links, zero unlinked provider fixtures, unchanged review queue (28 cases / 28 events), no identity approvals, and zero PIT feature promotion. Do not insert scores or canonical rows directly through SQL.

## 6. Stage 2 exit decision

Completed:
- Independent project/database isolation and production DB identity.
- Migrations 001–009 and canonical materialization.
- Historical import run 3, request ledger and raw-response provenance.
- Canonical identity review queue and fail-closed duplicate controls.
- 370-fixture structural reconciliation against the official 20-team double round-robin schedule, with the exact 10 missing directed pairings matching CBF Round 38.
- Source rights review and explicit PIT ineligibility decision.
- AI Midas snapshot pinning and anomaly quarantine.

Still open:
- Guarded canonical materialization of the 10 imported Round 38 fixtures, followed by independent production count/provenance verification.
- Human decisions on the 28 identity/coverage review cases; these must remain pending until a human reviews evidence. No automatic promotion is permitted.
- A future source/provider qualification that supplies defensible source-publication and availability timestamps for PIT features.

**Stage 2 status: close-ready, pending manual Round 38 canonical materialization and production verification.** Human identity decisions and PIT-source qualification remain explicit downstream gates; neither may be silently waived. No model training, feature engineering from PIT-ineligible data, prediction API activation, value-bet activation or Android/backend prediction integration is authorized by this audit.
