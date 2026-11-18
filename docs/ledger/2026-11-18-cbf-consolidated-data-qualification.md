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
| 31–38 | 80 | 80/80 | 8 official schedule changes accounted for; all 80 final kickoff times match | 15/80 verified; 65 pending (includes 7 new round-38 article checks) |
| **Total** | **380** | **380/380** | **42 official schedule changes; 2 research-only chronology corrections; 0 unresolved kickoff discrepancies after correction** | **315/380 verified; 65 pending** |

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

Latest report: [workflow 44281629472](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44281629472)

- Source observations: 384
- FINISHED labeled fixtures: 380
- UNKNOWN rows excluded: 4
- Provider-local teams in finished corpus: 20
- Invalid rows: 0
- Kickoff adjudications applied: 2
- Report SHA-256: `1eb2ff33999df3d9c83af5d89a9006fca6b3e096ef8b4b83285fc05aa69d8ca3`

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

The official CBF score table reconciles 290/290 fixtures in rounds 1–29. One PDF score conflict (Fortaleza–Operário, CBF ref 245) is resolved using the individual CBF match page and corroborating CBF news article; the raw PDF and provider rows are preserved. Official CBF result articles verify all 10 round-30 fixtures and all 10 round-38 fixtures. Three round-38 checks overlap the earlier individual match-page checks, so the round-38 article adds seven unique verified scores. Together with eight earlier individual match-page checks in rounds 31–38, total unique scorelines verified: **315/380**. The remaining **65** are in rounds 31–37. See the [rounds 1–29 score ledger](2026-11-18-cbf-score-verification-rounds-1-29.md), [round 30](2026-11-18-cbf-round30-score-verification.md), and [round 38](2026-11-18-cbf-round38-score-verification.md).

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

1. Complete official scoreline verification for the remaining 65 finished fixtures in rounds 31–37.
2. Complete human review of the 28 identity/quality cases; preserve all conflicting rows until signed off.
3. Implement forward-looking source snapshot capture with reliable pre-kickoff availability evidence and rights metadata.
4. Extend independent prospective validation across additional competitions/seasons.
5. Only then reconsider model selection, production publication and downstream Android integration.
