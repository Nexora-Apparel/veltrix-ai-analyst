# VELTRIX AI ANALYST — Stage 2 closure audit

**Audit date:** 2026-11-17  
**Scope:** Brazil Série B 2026 historical source qualification, fixture coverage, identity integrity, production provenance and point-in-time eligibility.  
**Database:** `veltrix_ai_analyst` (Neon project `young-wind-27772160`)  
**Provider:** 5DollarFootballAPI, competition `522514093`, source `5dollarfootballapi`

## Executive status

**Stage 2 is close-ready but not fully closed.** The historical foundation, migrations, canonical materialization, provenance audit and first-37-round matchup reconciliation are verified. One bounded final-round import remains blocked on a manual GitHub Actions dispatch because this session can inspect and update repository files but cannot trigger `workflow_dispatch` events. No credentials are exposed and no direct SQL fixture inserts will be used to bypass the provenance pipeline.

## 1. Production database and migration state

- Migrations 001–009 are applied; migration 009 was independently read-verified in production.
- Canonical layer: 21 teams, one competition, 374 canonical fixtures.
- Source links: 21 team links, one competition link, 374 fixture-source links.
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

The final 10 Round 38 records are not in historical import run 3 because its end boundary is 9 November. The 5Dollar historical import workflow is deliberately manual and gated. [PR #20](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/20) has merged as `69f91a99b162804fa6a1baa8cd35d9cdc3388488`. It adds timezone-aware half-open interval parameters, enforces the existing 40-request global ceiling, and creates a dedicated Round 38 workflow with the fixed `[2026-11-09T00:00:00Z, 2026-11-17T00:00:00Z)` interval and a four-request cap. The validator checks the actual persisted run boundaries and budget. CI run [#44102095868](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44102095868) passed backend tests, Ruff and Android debug APK build. The workflow is ready for manual dispatch. This session cannot dispatch GitHub Actions workflow events.

Required manual assistance:
1. [PR #20](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/20) is merged and CI is green.
2. Open [GitHub Actions — Controlled Brazil Serie B Round 38 Incremental Import](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/historical-brazil-serie-b-round38.yml) and dispatch with `confirm_collection=COLLECT_BRAZIL_SERIE_B_ROUND_38`. The workflow uses `[2026-11-09T00:00:00Z, 2026-11-17T00:00:00Z)` and a four-request budget.
3. Verify the run's sanitized report and independently read-check that the 10 fixtures are ingested with provider response IDs, payload hashes, source observations and sightings; confirm there are no duplicate or rejected writes.

No manual score insertion or migration bypass is acceptable.

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
- Bounded ingestion of the 10 final-round results through the approved 5Dollar provider path.
- Human decisions on the 28 identity/coverage review cases; these must remain pending until a human reviews evidence. No automatic promotion is permitted.
- A future source/provider qualification that supplies defensible source-publication and availability timestamps for PIT features.

**Stage 2 status: close-ready, pending the manual Round 38 incremental import.** Human identity decisions and PIT-source qualification remain explicit downstream gates; neither may be silently waived. No model training, feature engineering from PIT-ineligible data, prediction API activation, value-bet activation or Android/backend prediction integration is authorized by this audit.
