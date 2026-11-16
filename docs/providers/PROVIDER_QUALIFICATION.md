# Provider qualification register

This is the source-of-truth register for data providers in VELTRIX AI ANALYST. A provider is not production-ready merely because an adapter exists. Account access, competition coverage, data fields, rights, quotas, freshness and failure handling must be verified separately.

## 1. 5DollarFootballAPI

**Role:** Primary candidate for fixtures, results, competition metadata and available match-level fields.

**Existing project review**
- Legacy repository inspected: `Nexora-Apparel/veltrix-football`.
- The old `app/provider_adapters.py` is coupled to legacy prediction code and legacy fixture-identity helpers. It was not copied into this project.
- This repository contains a new isolated adapter at `backend/app/providers/five_dollar.py`, built against the new provider contracts. It contains no prediction code and does not persist data.

**Existing account evidence from the prior VELTRIX project**
- The same Community account was read-only verified on 2026-11-12: plan Community, 300 requests/hour, 20 requests/minute burst.
- The account exposed seven entitled competitions: Brazil Serie A `3118717965`, Brazil Serie B `522514093`, England Premier League `4160026622`, France Ligue 1 `3614399544`, Germany Bundesliga I `686337048`, Italy Serie A `3405541143`, and Spain La Liga `4212821298`.
- Brazil was the only country outside the top-five European leagues, inferred as the selected country pack from the returned catalogue.
- A read-only 365-day qualification on 2026-11-12 (old repository Actions run #43299701499) returned 2,496 finished fixtures with valid scores across all seven competitions, complete pagination (26 pages), 28 requests within a 40-request cap, zero duplicates, zero rejected/quarantined records, and no provider failure. It performed no database writes.
- This is useful prior evidence, not a substitute for rechecking the account when the new project secret is connected. Do not repeat the full historical pull merely to reconfirm access.
- Existing secret names in the prior repository are `FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY` and `FIVEDOLLARFOOTBALL_API_KEY`. The new adapter accepts these names and `FIVE_DOLLAR_FOOTBALL_API_KEY`; transfer the credential only through repository secrets or a local environment, never through source code.
- Recheck the current `/status` response and Brazil league list before the first import, then make only bounded incremental calls.

**Current public plan details checked 2026-11-16**
- Community Access: 300 requests/hour, with an additional 20 requests/minute burst ceiling.
- Community Access: top-five leagues plus one country pack.
- Community Access: 12 months of results and odds history.
- Community odds: Bet365 markets; do not assume other bookmakers are included.
- The plan comparison indicates fixture-list odds expansion is not available as one bulk request on Community; odds must be retrieved using the applicable per-fixture route.
- The public terms permit caching and use in the user's own product, but prohibit reselling/redistributing raw data as a competing feed. Attribution is required on public-facing products using Free/Community data; private/internal use is exempt.

**API contract verified from official docs**
- Base URL: `https://api.5dollarfootballapi.com/v1`.
- Authentication: `Authorization: Bearer <key>`.
- Runtime secret name for this project: `FIVE_DOLLAR_FOOTBALL_API_KEY`.
- `GET /leagues?country=BR&include=seasons`: competition discovery and available seasons.
- `GET /leagues/{id}/fixtures?start_time=...&end_time=...`: competition-specific fixture/result history; no 24-hour span cap.
- `GET /fixtures?start_time=...&end_time=...`: global window endpoint, maximum 24 hours per request.
- List endpoints are paginated with `page`, `per_page` (maximum 100), and `pagination.has_more`.
- Timestamps are UTC. The global fixtures endpoint accepts start-inclusive/end-exclusive Unix timestamps.
- The API uses `scheduled`, `in_play`, `finished`, and `unknown` fixture states. Only `finished` is confirmed as a settled result.
- HTTP 429 includes `Retry-After`; the adapter surfaces this to the scheduler and does not blindly retry in a tight loop.
- Retired league IDs may return HTTP 301 with `error.canonical_id`; the adapter raises a typed exception so the canonical mapping can be updated deliberately.

**Existing data-quality limitations**
- The old Phase 2 review found the 5Dollar historical odds-tick endpoint returned HTTP 403 on Community. Sampled timestamp coverage was 7/77 (9.09%), far below the later 98% odds timestamp requirement. Do not use Community odds as a verified historical tick archive or CLV source.
- The previous VELTRIX database held the schema and one acceptance audit but zero imported match rows; there is no populated old Neon history table to migrate.
- A separate 70,444-row Football-Data/ClubElo CSV artifact was quarantined because the underlying dataset rights did not permit assuming reuse. Do not import it.
 
**Implementation status**
- [x] Provider-neutral normalized fixture and provenance contract.
- [x] Competition metadata contract.
- [x] Isolated 5Dollar adapter for competition discovery.
- [x] Isolated 5Dollar adapter for global fixture windows and competition-specific history windows.
- [x] Pagination handling and request-window guardrails.
- [x] Timezone-aware timestamps and provenance metadata.
- [x] Explicit handling for missing credentials, malformed payloads, 429 and moved league IDs.
- [ ] CI green for the new adapter and its tests.
- [ ] Verify the actual account status/Community plan using the user's runtime secret.
- [ ] Verify the Brazil country pack and confirm Brazil Serie B availability by returned league IDs.
- [ ] Verify the historical date range actually available for each required competition.
- [ ] Verify field completeness for scores, corners, cards and any statistics used downstream.
- [ ] Implement odds ingestion separately; validate bookmaker, market, price timestamps and history semantics before use.
- [ ] Import historical records only after coverage and provenance qualification.

**Important odds restriction**
The presence of opening/closing prices in an API response does not automatically certify bookmaker-specific closing timestamps or CLV suitability. Preserve the raw price payload, bookmaker, market/line, and every supplied timestamp. Do not label an odds value as a verified closing price or use it for CLV claims until those semantics are proven.

## 2. AI Midas

**Role authorized by the user:** Historical football statistics and additional odds data, including Brazil Série B where available. Authorization was recorded on 2026-11-15 and is **non-commercial only**.

**Verified source snapshot found in the prior VELTRIX repository**
- Source repository: `aimidas1/aimidas1`.
- Pinned source commit: `29baca362a34ce5dcd3924b07ec9c7d5139d83fc`.
- Approved source record: `approval-aimidas-football-data-noncommercial-2026-11-15`.
- Brazil Série B file: `advanced stats/Brazil Serie B 2026.csv`.
- File SHA-256: `55b0c00629abd2d4ff3c31659ada950b67ffc2752609284b32c15c99f71152ab`.
- File size: 192,284 bytes; 738 team-match rows; 369 distinct matches; 20 teams; dates 2026-03-21 through 2026-11-08.
- The prior collector pinned exact Git blob SHA-1 `b6bdb94c053d2149e6232fb100e1f158e46e4533` and verified the single file without downloading the other archives.
- Prior source approval permits non-commercial collection, internal storage, historical import, analysis, feature research, training and validation within the approved scope. Attribution must be retained. Raw-source redistribution is not allowed.
- The source is a GitHub CSV snapshot, not a confirmed live AI Midas API. Do not invent an API base URL or authentication scheme.

**Qualification status**
- [x] User authorization recorded 2026-11-15; non-commercial-only scope.
- [x] Pinned Brazil Série B 2026 CSV and checksum evidence identified.
- [x] Prior code confirms read-only single-file snapshot capture and identity-reconciliation workflow.
- [ ] Reimplement a minimal snapshot collector in this repository; store raw files outside Git in a private/local data directory or private storage.
- [ ] Verify the exact source file bytes/hash again before ingesting.
- [ ] Review schema and fields before mapping; do not assume every column is a pre-match feature.
- [ ] Confirm whether other pinned AI Midas CSVs are in scope before collecting them.
- [ ] Identify the separate additional-odds source/schema, if any, and validate bookmaker/market/line/timestamp semantics.
- [ ] Keep attribution and non-commercial use restrictions attached to every imported record.

**Point-in-time and odds limitation**
The pinned Brazil Série B CSV has no verified source-publication timestamp or timezone-aware availability timestamp. The prior project explicitly marked it `point_in_time_certifiable=false`. It can support historical descriptive analysis, match identity checks and carefully scoped research; its post-match team statistics must not be used as pre-match features unless a valid availability timeline is independently established. Its odds fields, if any, are not certified bookmaker-specific closing prices and cannot support CLV claims without timestamp/market verification.

Do not guess that AI Midas is another similarly named odds provider. Do not substitute a different service's API documentation or credentials.

## 3. Legacy source reuse decision

The old VELTRIX FOOTBALL repository may be inspected for generic transport behaviour, pagination patterns, response-field mappings and historical ingestion safeguards. Reuse only after review and tests.

Do not copy:
- Legacy prediction or probability calculations.
- Legacy model weights, priors, calibration or publication rules.
- Modules that import legacy prediction code merely to normalize provider data.
- Credentials, secret values, production environment files or mutable production database state.

Provider IDs remain provider-local unless a verified crosswalk exists. Preserve raw source identifiers and provenance. Cross-provider fixture matching must be conservative and ambiguous matches must be quarantined rather than merged.

## 4. Official references

- API documentation: https://5dollarfootballapi.com/docs
- Fixture list endpoint: https://5dollarfootballapi.com/docs/fixtures
- League fixture endpoint: https://5dollarfootballapi.com/docs/league-fixtures
- Account status endpoint: https://5dollarfootballapi.com/docs/status
- Community Access plan and history: https://5dollarfootballapi.com/docs/changelog
- Pricing comparison: https://5dollarfootballapi.com/pricing
- Terms of Service: https://5dollarfootballapi.com/terms

Review these references again before production activation; provider plans and API behaviour can change.
