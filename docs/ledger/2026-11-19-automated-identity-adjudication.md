# VELTRIX automated identity adjudication evidence ledger

**Date:** 2026-11-19  
**Policy:** `cbf-2026-identity-adjudication-v1`

## Safety boundary

This ledger supports automated evidence decisions for the 2026 Brazil Série B canonical identity cases and the identified England Premier League duplicate candidate. An automated confirmation records the evidence-based disposition; it does not authorize deleting provider records, merging canonical teams, rewriting source payloads, or certifying historical point-in-time availability. Raw provider rows and append-only provenance remain intact. Duplicate/alias candidates are retained and excluded from settled-label use.

## Brazil Série B: 20 active team identities

The 20 active 5DollarFootballAPI provider team IDs each appear in exactly 38 FINISHED fixtures: 19 home and 19 away. Their ordered home/away fixture pairings reconcile to the official CBF 2026 Série B schedule (380/380). The official schedule and match records verify the competition's participating clubs and their results.

| Provider team ID | Provider label | CBF 2026 club |
|---:|---|---|
| 1102583842 | America MG | América-MG |
| 1446563615 | Avai | Avaí |
| 1548718709 | Ponte Preta | Ponte Preta |
| 1620921678 | Novorizontino | Grêmio Novorizontino |
| 1657329649 | Ceara | Ceará |
| 1684426968 | Atletico GO | Atlético-GO |
| 2016651568 | Operario PR | Operário-PR |
| 2434042650 | Vila Nova | Vila Nova |
| 2651466053 | CRB | CRB |
| 2672186301 | Juventude | Juventude |
| 3007875643 | Athletic Club MG | Athletic-MG |
| 3126624865 | Goias | Goiás |
| 3219034225 | Londrina | Londrina |
| 3250670103 | Botafogo SP | Botafogo-SP |
| 3324195045 | Criciuma | Criciúma |
| 4227927162 | Cuiaba | Cuiabá |
| 4267737771 | Nautico | Náutico |
| 559667509 | Sport Recife | Sport |
| 744720326 | Fortaleza | Fortaleza |
| 844813267 | Sao Bernardo | São Bernardo |

Evidence: [CBF official 2026 Série B table and schedule](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026?doc=Tabela+Detalhada), [CBF detailed schedule](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Brasileiro_Serie_B_2026_23_09_378b396600.pdf), and the [full-season identity evidence audit](2026-11-18-cbf-team-identity-evidence-audit.md). Provider spelling variants are preserved; no provider ID is rewritten.

## América-MG alias candidate

Provider ID `1102583842` (`America MG`) has 38 FINISHED appearances and matches the official CBF América-MG schedule. Provider ID `3808811746` (`América Mineiro`) appears only in the UNKNOWN Goiás–América duplicate row and has zero FINISHED appearances. CBF records one Round 1 fixture, Goiás 3-1 América, on 22 March 2026. The alternate provider ID is therefore adjudicated as a duplicate/alias candidate, not a second active club. Both source IDs and all raw rows remain preserved; no canonical team merge is performed.

Evidence: [CBF Goiás 3-1 América match page](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/goias-x-america/832843).

## Duplicate fixture candidates

The four Brazil Série B UNKNOWN rows are confirmed duplicate/stale candidates and are flagged as conflicts. The corresponding FINISHED rows match official CBF match pages:

| Match | FINISHED provider ID | UNKNOWN provider ID | Official CBF result |
|---|---:|---:|---|
| Goiás–América-MG | 3116209225 | 2341822348 | 3-1, 22 Mar 2026 |
| Fortaleza–Londrina | 1587564237 | 2336910968 | 3-0, 23 May 2026 |
| Fortaleza–Botafogo-SP | 236839304 | 933498248 | 1-0, 28 Jul 2026 |
| Ceará–Londrina | 553958702 | 1988139832 | 2-1, 22 Aug 2026 |

Evidence: [Goiás–América](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/goias-x-america/832843), [Fortaleza–Londrina](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-londrina-saf/832976), [Fortaleza–Botafogo](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-botafogo/833076), [Ceará–Londrina](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/ceara-x-londrina-saf/833116).

The England Premier League candidate is also confirmed: the FINISHED Man City 0-1 Brighton row on 31 October 2026 matches the official club match record; the paired UNKNOWN row is one minute later with the same teams. The FINISHED row remains source-verified and the UNKNOWN row remains CONFLICT.

Evidence: [Manchester City official match record](https://www.mancity.com/matchday/fixtures/mens/2026/premier-league/man-city-v-brighton-31-oct-2026).

## Competition and season coverage

Provider competition ID `522514093` is Brazil Série B 2026. The CBF official schedule confirms the competition identity. The imported run-3 interval contains 370 FINISHED fixtures through 9 November 2026 (rounds 1–37); Round 38 is outside that interval. The full-season evidence ledger reconciles all 380 fixtures, ordered pairings, kickoff chronology and scorelines against CBF records. This confirms the declared run-3 coverage window; it does not grant PIT eligibility.

Evidence: [CBF official 2026 Série B table and schedule](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026?doc=Tabela+Detalhada), [consolidated 2026 CBF qualification ledger](2026-11-18-cbf-consolidated-data-qualification.md).

## Historical PIT disposition

The historical 374-observation gap (384 for the full competition corpus) has no verified source-publication or `available_at` timestamps. Those historical observations are permanently excluded from PIT-certified pre-match feature inputs unless new original timestamp evidence is recovered. Retrieval time, kickoff time and final schedule data are not substitutes. The case is automatically deferred as non-actionable for this release; future prospective captures remain eligible only under strict pre-kickoff system-observed timestamp rules.

Evidence: [historical PIT evidence audit](2026-11-18-historical-pit-evidence-audit.md).

## Automated decision semantics

- `AUTOMATED_CONFIRMED`: evidence supports the case disposition; no destructive merge or source-row mutation is implied.
- `AUTOMATED_DEFERRED`: no safe historical correction exists; affected records remain excluded from the relevant production dataset.
- The effective review queue no longer requires a human action for these dispositions.
- `effective_canonical_team_aliases` and `effective_canonical_fixture_deduplication` remain HUMAN_CONFIRMED-only. Automated evidence never triggers canonical merging or deletion.
