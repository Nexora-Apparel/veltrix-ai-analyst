# 2026-11-18 — Aston Villa vs Sunderland 5Dollar odds snapshot qualification

## Scope

This ledger records the bounded 5DollarFootballAPI Community fixture-odds probe for canonical fixture `4042864659` (Aston Villa home vs Sunderland away; Premier League; kickoff `2026-11-21T15:00:00Z`). It is a provider-access and schema qualification record only.

## Workflow evidence

- Workflow run: [#44235738600](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44235738600)
- Job: [#134571320812](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44235738600/job/134571320812)
- Probe workflow commit: `ca06bf5009346c5e7c4168045e493c30ec80d8c4`
- Artifact: [5dollar-odds-snapshot-probe](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44235738600/artifacts/14397321771)
- Artifact ID: `14397321771`; archive SHA-256: `51c9db192ccd89e11f2514858af6b4bb7b0d83e93ff04a075287ee6d2cd851ef`
- HTTP status: 200; access result: `ODDS_SNAPSHOT_ACCESS_CONFIRMED`
- Endpoint: `GET /v1/fixtures/4042864659/odds`
- Exactly one request; zero retries; no pagination; no database write.
- Request start: `2026-11-18T04:12:59.685442Z`
- Local retrieval: `2026-11-18T04:13:00.038394Z`
- Provider HTTP Date: `Wed, 18 Nov 2026 04:13:00 GMT`
- Response bytes: 2,282
- Response SHA-256: `5786a32f5e5b384b5b451e6caf311397751a3695ed999fb4ab88fe992f83fc78`
- Community rate limit: 299 remaining of 300 at response time.

## Returned bookmaker and market data

One bookmaker row was returned: Bet 365, slug `bet365`. Twelve market keys were present: `1x2`, `asian_handicap`, `asian_handicap_half`, `btts`, `card_asian`, `card_line`, `corner_asian`, `corner_line`, `corner_line_half`, `goal_line`, `goal_line_fixed`, `goal_line_half`.

Bet365 1X2 opening:
- Home (Aston Villa): 1.90
- Draw: 3.50
- Away (Sunderland): 3.90
- Provider `opened_at`: `2026-10-31T19:12:59Z`

Closing object exposed only the fields `home`, `draw`, and `away`; no closing prices or closing timestamp were included in the compact manifest.

## Cross-provider comparison disposition

The Odds API event-specific H2H probe for the same exact fixture was already captured in run [#44228137046](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44228137046):
- Exact fixture identity and orientation matched: Aston Villa vs Sunderland; kickoff `2026-11-21T15:00:00Z`.
- One UK H2H request returned 63 complete timestamped quotes across 21 bookmakers.
- Local retrieval was `2026-11-18T03:07:24.485966Z`; source ticks were approximately 03:05:58–03:07:11Z.
- The compact manifest's 21-bookmaker set did not include Bet365. Therefore a same-bookmaker Bet365 price comparison is not possible from these captures.
- The 5Dollar Bet365 opening timestamp is 2026-10-31, while the response was first retrieved locally on 2026-11-18. The Odds API quotes were retrieved on 2026-11-18 and represent contemporaneous quote ticks. These are not temporally aligned observations.
- Accordingly, **no valid same-time price comparison, provider coverage superiority claim, PIT admission, CLV benchmark, or value-betting conclusion is established**. The two captures prove fixture-specific provider access and schema availability only.

## Quota accounting

- 5Dollar: one fixture odds request; last response header showed 299/300 remaining.
- The Odds API: no additional request was made for this follow-up. Its last confirmed account balance after the earlier single H2H probe remains 270 credits; do not treat this as a live balance.

## Architecture and safety disposition

- The result is for the secondary value-betting research path only.
- Bookmaker odds remain excluded from core prediction generation: no features, priors, overrides, required dependencies, or model inputs.
- No raw odds persistence, Neon writes, recurring collection, production prediction publication, value-bet activation, CLV claim, or model promotion is authorized by this probe.
- A 5Dollar snapshot retrieved after its provider opening timestamp does not prove the system had access to that price at opening. PIT requires local retrieval no later than the prediction cutoff; source tick/open time cannot substitute for local availability.

## Next engineering unit

Implement pure typed prospective odds-capture contracts and tests before any writer or schedule:
1. Preserve request-start, local-retrieval, provider-Date, source-tick/open, kickoff, and prediction-cutoff clocks independently.
2. Validate exact fixture identity, bookmaker, market, selection, line, decimal price, aware UTC timestamps, response hash, rights scope, and pre-match state.
3. Fail closed unless local retrieval is at or before prediction cutoff.
4. Make idempotency deterministic and test duplicate/conflicting observations.
5. Keep capture manual and one-fixture/one-request; no retries, pagination, history, bulk odds or DB writes in this phase.
6. Keep odds entirely outside the independent core prediction model.
