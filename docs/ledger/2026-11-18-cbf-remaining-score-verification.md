# CBF Série B 2026 — remaining scoreline verification (2026-11-18)

## Scope and result

- Workflow: [run 44286701796](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44286701796)
- Evidence artifact: [cbf-remaining-score-verification](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44286701796/artifacts/14419317538)
- Artifact SHA-256: `c1d6051e02f3b5d39a9ee61374e586241747b876c7887e4651944067e515d3f3`
- Database: `veltrix_ai_analyst`; read-only transaction
- Provider: 5DollarFootballAPI; competition `522514093`
- Source: 27 individual official CBF match pages, with CBF detailed schedule PDFs used for match-reference IDs
- Raw provider rows changed: 0

<badge> <badge/> 

**27 / 27 verified; 0 mismatches; 0 missing fixtures.**

| Round | CBF refs | Fixtures | Verified |
|---:|---:|---:|---:|
| 31 | 301–310 | 10 | 10/10 |
| 32 | 311–320 | 10 | 10/10 |
| 37 | 362–368 | 7 | 7/7 |
| **Total** | | **27** | **27/27** |

Each registry row records the provider fixture ID, exact provider home/away labels, official CBF individual match-page URL and official score. The audit compared those values against the exact immutable provider fixture row and required `FINISHED` status.

## Unique corpus accounting

This pass covers precisely the 27 outstanding scorelines after the earlier 353/380 unique verifications. No overlap was included in this registry. The complete 380-fixture CBF Série B 2026 finished corpus is now **380/380 score-verified**:

- Rounds 1–29: 290/290
- Round 30: 10/10
- Rounds 31–32 and 37: 27/27 (this pass)
- Rounds 33–36: 40/40, including two overlaps with earlier checks
- Round 38: 10/10, including three overlaps with earlier checks

The total is unique fixture coverage, not the sum of overlapping audit passes.

## Boundaries

- Provider-local fixture IDs and exact provider team labels were checked; no canonical team merge or alias approval is implied.
- No production rows were modified.
- This resolves scoreline verification only; it does not establish historical PIT availability, source rights, season completeness beyond this CBF competition, or canonical identity decisions.
