# CBF 2026 Série B — consolidated data qualification status (2026-11-18)

## Executive result

The 380-fixture finished corpus now has full fixture-reference, ordered home/away pairing and kickoff chronology reconciliation against official CBF schedules. Two evidence-backed research-only timestamp corrections are applied. The raw provider fixtures and source observations remain immutable.

This does **not** make the corpus PIT-certified or the model production-ready. Scoreline verification and canonical identity review remain incomplete.

## Schedule and chronology coverage

| CBF rounds | Fixtures | Ordered pairings | Schedule result | Scoreline verification |
|---|---:|---:|---|---|
| 1–18 | 180 | 180/180 | 26 official schedule changes confirmed; 1 provider timestamp precision discrepancy corrected in research layer; 0 unexplained differences | 180/180 verified |
| 19–24 | 60 | 60/60 | 2 official schedule changes accounted for; all 60 final kickoff times match | 60/60 verified |
| 25–30 | 60 | 60/60 | 6 official schedule changes accounted for; ref 262 corrected in research layer | 60/60 verified (50 from CBF PDF; 10 from CBF round-30 articles) |
| 31–38 | 80 | 80/80 | 8 official schedule changes accounted for; all 80 final kickoff times match | 80/80 verified (all 80 scores now cross-checked against official CBF match pages or round-results articles) |
| **Total** | **380** | **380/380** | **42 official schedule changes; 2 research-only chronology corrections; 0 unresolved kickoff discrepancies after correction** | **380/380 verified** |

The 42 official schedule changes are 26 in rounds 1–18, 2 in rounds 19–24, 6 in rounds 25–30 and 8 in rounds 31–38. Provider kickoff timestamps were compared in `America/Sao_Paulo`; final CBF match pages were used for the changed fixtures.

The two research-only chronology corrections are:
- CBF ref 6, Goiás x América, provider fixture `3116209225`: 17:58:35 BRT → official 18:00 BRT.
- CBF ref 262, São Bernardo x Londrina, provider fixture `2179333578`: 20:49:59 BRT → official 19:30 BRT.

Both corrections are stored in `backend/data/research/official_kickoff_adjudications.json`. Neither raw provider row nor source observation was changed.

Detailed evidence:
- [Rounds 1–18](2026-11-18-cbf-rounds-1-18-reconciliation.md)
- [Rounds 19–24](2026-11-18-cbf-rounds-19-24-reconciliation.md)
- [Rounds 25–30](2026-11-18-cbf-rounds-25-30-reconciliation.md)
- [Rounds 31–38](2026-11-18-cbf-rounds-31-38-fixture-reconciliation.md)

## Corrected retrospective research

Latest corrected report: [workflow 44286437268](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44286437268); [corrected report artifact](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44286437268/artifacts/14419186651); [paired diagnostics artifact](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44286437268/artifacts/14418483224).

- Source observations: 384
- FINISHED labeled fixtures: 380
- UNKNOWN rows excluded: 4
- Provider-local teams in finished corpus: 20
- Invalid rows: 0
- Kickoff adjudications applied: 2
- Independently cross-checked official CBF scores: 353/380; 27 pending
- Corrected report SHA-256: `2a411e223508db929c63e26185798c9c94f36dc1ddc2c81a8a9b76d97388fd80`
- Paired diagnostics: 2,000 moving-block bootstrap resamples, block size 20; every pairwise 95% interval crosses zero.
- Detailed report: [corrected retrospective research report ledger](2026-11-18-corrected-retrospective-research-report.md)

| Model | Brier | Log loss |
|---|---:|---:|
| Elo | 0.63336366 | 1.05113130 |
| Poisson | 0.63054946 | 1.04804403 |
| Adaptive ensemble | 0.62933489 | 1.04588885 |

The adaptive ensemble has the best point estimates, but all paired moving-block bootstrap 95% confidence intervals cross zero. No model is selected or promoted from this retrospective result.

## Historical point-in-time evidence

The production audit found 384 source observations and 384 sightings for the competition: zero source-publication timestamps, zero `available_at` timestamps, all 384 sightings marked `RETRIEVED_AT_ONLY`, and zero PIT-certifiable sightings. See the [historical PIT evidence audit](2026-11-18-historical-pit-evidence-audit.md). The historical corpus remains ineligible for PIT-certified pre-match features; no timestamps were backfilled.

## Remaining qualification blockers

### 1. Scoreline verification

The official CBF score table reconciles 290/290 fixtures in rounds 1–29. One PDF score conflict (Fortaleza–Operário, CBF ref 245) is resolved using the individual CBF match page and corroborating CBF news article; the raw PDF and provider rows are preserved. Official CBF result articles verify all 10 round-30 fixtures, all 10 round-38 fixtures, and all 40 fixtures in rounds 33–36. The 33–36 article pass has two overlaps with previously checked individual match pages (refs 325 and 360); the round-38 article has three overlaps (refs 371, 372 and 374). The final 27 outstanding fixtures (rounds 31–32 and 37) were then cross-checked against individual official CBF match pages, with 27/27 matches, 0 mismatches and 0 missing provider fixtures. **All 380/380 scorelines are now verified.** See the [rounds 1–29 score ledger](2026-11-18-cbf-score-verification-rounds-1-29.md), [round 30](2026-11-18-cbf-round30-score-verification.md), [rounds 31–32 and 37](2026-11-18-cbf-rounds-31-32-37-score-verification.md), [rounds 33–36](2026-11-18-cbf-rounds-33-36-score-verification.md), and [round 38](2026-11-18-cbf-round38-score-verification.md).

### 2. Canonical identity review

The current database reports 28 identity/quality review cases, all with `HUMAN_REVIEW_REQUIRED`:

| Case type | Cases |
|---|---:|
| Team real-world identity candidates | 20 |
| Fixture duplicate candidates | 4 |
| Competition real-world identity candidate | 1 |
| Team alias candidate | 1 |
| PIT timestamp gap | 1 |
| Season coverage reconciliation | 1 |
| **Total** | **28** |

No team alias, duplicate fixture, competition mapping or canonical merge has been automatically approved. In particular, provider IDs `1102583842` (America MG) and `3808811746` (América Mineiro) remain a likely alias/duplicate pair, not a confirmed merge.

### 3. Historical PIT evidence

The 384 historical provider observations have no source-publication or `available_at` timestamps and none is PIT-certifiable. Retrieval after the event cannot establish pre-match availability. This historical gap cannot be repaired by inventing timestamps or by using final match schedules.

Future ingestion must capture immutable source payloads and verified observation/availability timestamps before kickoff, with source rights and publication metadata. Historical records stay excluded from PIT-certified feature inputs.

### 4. Coverage and competition identity

The API import windows reconcile internally, but the provider catalogue does not independently prove complete season coverage or all competition metadata. The 1 season-coverage review case and 1 competition-identity case remain open for human evidence review.

## Controls retained

- Raw 5DollarFootballAPI fixtures and source observations remain immutable.
- 5DollarFootballAPI remains the primary source.
- No bookmaker odds entered core model features or inference.
- No Odds API credits were consumed.
- No production model promotion.
- Value betting remains locked.
- Android prediction integration remains deferred until real prediction endpoints and validation gates exist.
- No historical PIT eligibility is granted by the schedule reconciliation.

## Next sequence

1. Scoreline verification is complete: 380/380 finished fixtures cross-checked against official CBF evidence.
2. Complete human review of the 28 identity/quality cases; preserve all conflicting rows until signed off.
3. Implement forward-looking source snapshot capture with reliable pre-kickoff availability evidence and rights metadata.
4. Extend independent prospective validation across additional competitions/seasons.
5. Only then reconsider model selection, production publication and downstream Android integration.
