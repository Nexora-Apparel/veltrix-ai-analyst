# Bookmaker Odds Use Boundary — VELTRIX AI ANALYST

**Effective:** 2026-11-18  
**Status:** Project policy; supersedes broader provider-use descriptions for this repository's bookmaker-odds records.

## Governing architecture

Bookmaker odds are restricted to the downstream value-betting subsystem. They are not eligible for core prediction feature engineering, training, validation, inference, probability calibration or prediction publication. This internal restriction applies even where a provider's general terms permit broader statistical or machine-learning uses.

The core football prediction engine must produce probabilities independently from eligible football-match data. The value-betting subsystem may consume those already-generated probabilities and separately approved, time-eligible bookmaker prices. Odds availability or failure must never suppress an otherwise eligible core forecast.

## Permitted bookmaker-odds uses

Subject to each provider's exact approval record:
- bounded collection and internal storage;
- internal price analysis and margin removal;
- downstream value-betting expected-value calculations;
- price comparison and prospective CLV research only when decision-time and source-timestamp evidence qualifies;
- internal cache within approved scope.

Not permitted:
- core prediction feature engineering, model training, model validation or inference;
- use as hidden priors, overrides, shortcuts or probability inputs;
- raw odds redistribution or resale;
- commercial use;
- any provider, sport, competition, market, endpoint or plan scope not explicitly approved.

## Provider scopes

### The Odds API
The published terms reviewed 2026-11-18 permit broad analytical and derived-value uses. The project approval is deliberately narrower: seven reviewed soccer sport keys only, non-commercial, bookmaker odds for value betting only, no raw redistribution. The existing account and quota remain subject to the separate operational ledger. Terms review: [THE_ODDS_API_TERMS_REVIEW.md](THE_ODDS_API_TERMS_REVIEW.md).

### 5DollarFootballAPI Community
The project has a separate odds approval distinct from its fixture/results approval. Scope is restricted to the seven observed Community competition IDs and bookmaker-odds data type, for value betting only. Community historical odds-history access is not assumed; the observed historical endpoint restriction and timestamp gaps prevent claims of a reliable historical quote archive or CLV coverage. No Ultra-only endpoint is authorized. Terms review: [5DOLLAR_TERMS_REVIEW.md](5DOLLAR_TERMS_REVIEW.md).

## Decision-time and data-quality requirements

For a candidate value-bet decision, local retrieval must occur no later than the immutable value-bet decision cutoff. Preserve request start, retrieval, provider HTTP Date, source tick, fixture kickoff and decision cutoff as distinct clocks. Provider-reported opening/recorded timestamps do not prove local availability. Require exact fixture identity, bookmaker, market, selection, line, valid decimal price, active provider/scope/data-type/use approval, response hash and idempotent observation identity. Reject stale, suspended, in-play, malformed, incomplete or ambiguous prices. No recommendation is emitted when odds fail these gates.

## Release status

This policy does not activate an odds collector, database writer, recurring schedule, value-bet recommendation, production prediction endpoint or model promotion. Value betting remains locked until its independent certification requirements pass.
