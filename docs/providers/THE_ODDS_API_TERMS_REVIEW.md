# The Odds API Terms Review — VELTRIX AI ANALYST

**Reviewed:** 2026-11-18  
**Terms version:** Last updated 2026-08-31  
**Official terms:** https://the-odds-api.com/terms-and-conditions.html  
**Official API documentation:** https://the-odds-api.com/liveapi/guides/v4/

## Reviewed permissions

The published Terms and Conditions expressly permit:
- storing API data and retaining it indefinitely;
- displaying data in websites, mobile applications, dashboards and analytical tools;
- research and analytical dashboards;
- calculating and displaying derived values;
- training statistical and machine-learning models.

The terms permit commercial use only where the provider's data is not the primary product being sold or redistributed. This project applies a stricter internal policy: the approval below is non-commercial only.

## Restrictions retained

The terms prohibit reselling, repackaging or redistributing the provider's data as a standalone data product, including through an API, data feed or downloadable raw-data files. Raw redistribution is therefore not approved. The provider does not require attribution, but this project will retain source attribution in internal provenance.

## Exact scope approved in this repository (seven sport keys aligned to the seven reviewed 5Dollar competition scopes)

This review is limited to the following soccer sport keys, selected because they correspond to competitions already in the project's approved 5DollarFootballAPI scope:
- `soccer_brazil_campeonato`
- `soccer_brazil_serie_b`
- `soccer_epl`
- `soccer_france_ligue_one`
- `soccer_germany_bundesliga`
- `soccer_italy_serie_a`
- `soccer_spain_la_liga`

Approved data types: soccer sports catalogue metadata, event catalogue metadata, and bookmaker odds observations. Approved uses: collection, storage, internal analysis, feature engineering, model training, model validation, benchmarking, cache and public display in this personal application. Commercial use and raw redistribution remain disabled by project policy.

## Operational conditions

- API credentials remain private in GitHub Actions secrets.
- Event discovery uses only the quota-free event endpoint documented by the provider.
- Odds-market requests remain manually bounded and quota-controlled.
- Each odds observation must preserve source, bookmaker, market, selection, line, provider update timestamp, local request/retrieval timestamps, response hash and exact fixture identity.
- Provider timestamps do not prove local availability. PIT admission requires local retrieval no later than the prediction cutoff.
- No raw odds feed may be exposed as a standalone product.
- Terms may change; re-review is required before expanding scope or changing use.

## Decision

The published terms support personal internal collection, retention, analysis and statistical/ML training within the exact sport-key scope above. This approval does not certify data quality, timestamp completeness, PIT eligibility, event-to-fixture matching, predictive performance or the account's current quota/plan.
