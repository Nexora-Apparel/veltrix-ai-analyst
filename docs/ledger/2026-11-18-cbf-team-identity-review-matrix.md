# 2026-11-18 — CBF team identity review matrix (candidate evidence only)

## Purpose and boundary

This matrix prepares the 21 provider team identity cases for human review against the official CBF 2026 Série B schedule. It does not confirm any mapping, merge provider IDs, alter canonical IDs, or authorize fixture deduplication.

Official source used as participation/name evidence:
- CBF, Campeonato Brasileiro Série B — Tabela Básica / Edição 2026, updated 23 September 2026: https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Brasileiro_Serie_B_2026_23_09_378b396600.pdf

The source establishes the official competition's listed club names and fixture pairings. It does not itself establish the identity of a 5Dollar provider ID. Each row therefore remains a candidate requiring reviewer confirmation.

## Candidate review matrix

| Provider team ID | Provider label | CBF schedule label candidate | Canonical team ID | Current disposition |
|---|---|---|---|---|
| 1102583842 | America MG | América MG | 08d164b5-b56e-42dc-8246-315a0cfce0d8 | REVIEW_REQUIRED |
| 1446563615 | Avai | Avaí | 8fb01e04-1d8d-4ca0-b4d4-cf4512589b69 | REVIEW_REQUIRED |
| 1548718709 | Ponte Preta | Ponte Preta | e5f8f231-2776-41b8-aac6-fe9a4b340d3c | REVIEW_REQUIRED |
| 1620921678 | Novorizontino | Novorizontino | 324b7fea-65cb-4fed-90f0-69b943be484b | REVIEW_REQUIRED |
| 1657329649 | Ceara | Ceará | c92ddfaf-67a0-4a88-ba75-7f64ec7ffdc9 | REVIEW_REQUIRED |
| 1684426968 | Atletico GO | Atlético GO | a9a22144-d1fe-4dd8-ae7b-72282b38b87e | REVIEW_REQUIRED |
| 2016651568 | Operario PR | Operário PR | 84d8443f-1bb1-4577-b694-3b80e231d85f | REVIEW_REQUIRED |
| 2434042650 | Vila Nova | Vila Nova | 595cd5de-fc28-4b41-ab95-0f75bda7b937 | REVIEW_REQUIRED |
| 2651466053 | CRB | CRB | 9f474b87-25eb-4269-b1d6-12fc61779d62 | REVIEW_REQUIRED |
| 2672186301 | Juventude | Juventude | 3d44a0e6-de86-4909-ba69-763ef4e9f6f8 | REVIEW_REQUIRED |
| 3007875643 | Athletic Club MG | Athletic MG | 9fbb972a-f0a7-4c17-8bf5-455cba45cd53 | REVIEW_REQUIRED |
| 3126624865 | Goias | Goiás | 41149b01-77c0-418a-9685-eeab3441f0e0 | REVIEW_REQUIRED |
| 3219034225 | Londrina | Londrina | f6b166f7-78c3-446b-86ce-86d986841154 | REVIEW_REQUIRED |
| 3250670103 | Botafogo SP | Botafogo SP | 58d14598-2d6d-430c-b008-5cd2bddf39b2 | REVIEW_REQUIRED |
| 3324195045 | Criciuma | Criciúma | 2cd15f93-20a8-4754-a9b3-0de1169890a8 | REVIEW_REQUIRED |
| 3808811746 | América Mineiro | América MG | ae7e562a-99e3-48ba-be39-25843e74fa05 | ALIAS_CANDIDATE — DO NOT MERGE |
| 4227927162 | Cuiaba | Cuiabá | 47eb5779-1e29-4a16-bb73-de204e21b015 | REVIEW_REQUIRED |
| 4267737771 | Nautico | Náutico | 0c01ffc1-5c19-4543-a04c-672ac0ff1f48 | REVIEW_REQUIRED |
| 559667509 | Sport Recife | Sport PE | ed4c5c1f-1e1f-4713-88da-29e28da4aa64 | REVIEW_REQUIRED |
| 744720326 | Fortaleza | Fortaleza CE | c6517c47-52b2-4cef-929d-616b30e51c95 | REVIEW_REQUIRED |
| 844813267 | Sao Bernardo | São Bernardo FC SP | 22847495-3a95-4ca1-b0ce-0ef2eef79ac4 | REVIEW_REQUIRED |

## Specific alias candidate

The existing audit case `BRAZIL_SERIE_B_RUN_3_TEAM_ALIAS_AMERICA_MG` reports:
- `1102583842` (`America MG`) appears in 37 fixtures.
- `3808811746` (`América Mineiro`) appears only in the duplicate UNKNOWN Goiás row.
- CBF identifies the Round 1 match as Goiás 3–1 América MG.

This is strong evidence that the two provider IDs may represent one real-world club. It is not a human decision. Preserve both provider identities and their canonical rows until the reviewer records a signed-off identity decision with evidence URI and checksum.

## Required reviewer procedure

For each candidate:
1. Confirm the official CBF club identity and competition participation.
2. Compare the provider team's home/away fixture graph against the CBF schedule, not name similarity alone.
3. Check the complete fixture sample for contradictions or cross-competition collisions.
4. Record reviewer identity, review timestamp, evidence URI and SHA-256 checksum.
5. Keep unresolved or conflicting rows in REVIEW_REQUIRED/CONFLICT status.

No automated canonical merge is permitted from this matrix. Fixture reconciliation and PIT timestamp qualification remain independent gates.
