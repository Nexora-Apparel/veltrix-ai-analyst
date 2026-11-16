# Provider qualification register

This is the source-of-truth register for data providers in VELTRIX AI ANALYST. A provider is not production-ready merely because an adapter exists. Account access, competition coverage, data fields, rights, quotas, freshness and failure handling must be verified separately.

## 1. 5DollarFootballAPI

**Role:** Primary candidate for fixtures, results, competition metadata and available match-level fields.

**Existing project review**
- Legacy repository inspected: `Nexora-Apparel/veltrix-football`.
- The old `app/provider_adapters.py` is coupled to legacy prediction code and legacy fixture-identity helpers. It was not copied into this project.
- This repository contains a new isolated adapter at `backend/app/providers/five_dollar.py`, built against the new provider contracts. It contains no prediction code and does not persist data.

**User/account direction already established**
- Community Access was selected/accepted in the prior VELTRIX project with the Brazil country pack.
- This does not prove the account currently has the Community plan or that Brazil's required leagues are enabled. Verify using the account status endpoint and league listing before importing anything.

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

**Role authorized by the user:** Historical football statistics and additional odds data, including Brazil Série B where available.

**Qualification status**
- [x] User authorization recorded in project context on 2026-11-15.
- [ ] No AI Midas adapter or confirmed implementation was found in the inspected legacy repository.
- [ ] Official API documentation, base URL, authentication method and response schema must be identified before coding the adapter.
- [ ] Confirm which historical statistics and competitions are actually available.
- [ ] Confirm bookmaker identity, market/line fields and timestamp semantics for odds.
- [ ] Confirm provider terms, storage rights, quota and historical retention.
- [ ] Verify Brazil Série B coverage from an actual account response where available.

**Explicit limitation**
Authorization to use AI Midas as a source does not certify timestamped bookmaker-specific closing odds or CLV suitability. Treat odds as supplemental, provenance-labelled observations until their timestamps and semantics are independently verified.

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
