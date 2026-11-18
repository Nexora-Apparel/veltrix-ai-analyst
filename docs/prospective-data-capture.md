# Prospective pre-match evidence and dataset protocol

## Capture source

The primary capture source is 5DollarFootballAPI. Fixture requests use the league-scoped fixtures endpoint with `include=stats,events` and deliberately omit bookmaker odds. The API documents a 50-row page limit when statistics/events are included.

The scheduled capture workflow runs daily and collects yesterday and today's fixture window for the seven approved competitions. It uses one shared provider client with a 60-second request pacer and a four-request per-competition budget. The workflow stops before provider requests unless migrations 012 and 013 are present.

## Evidence retained

For each response and fixture sighting, the database retains:

- Provider response ID and request event linkage
- Exact request/retrieval timestamp and database-generated SYSTEM_OBSERVED_AT
- HTTP status and response headers
- SHA-256 of the raw response body
- SHA-256 of the normalized fixture payload
- Provider fixture ID, competition ID, home/away provider team IDs and kickoff timestamp
- Fixture status, score, corners, cards, statistics and event payload when supplied

Raw response and observation records remain append-only. Repeated identical payloads create new sightings rather than overwriting the original observation. A prior observation's original timestamp is never rewritten to make it appear prospective.

## Pre-match eligibility

A feature observation is eligible for target fixture T only when:

1. Its sighting uses SYSTEM_OBSERVED_AT and is point-in-time certifiable.
2. Its provider response ID, retrieval timestamp, response timestamp and raw/normalized hashes reconcile.
3. Its system-observed timestamp is no later than the target prediction cutoff.
4. Its source fixture kickoff is strictly earlier than the target fixture kickoff.
5. Its competition, provider fixture ID, team IDs and kickoff agree with the immutable source payload.
6. Source approval was valid for feature engineering and model training at the target cutoff.

The database trigger in migration 013 enforces the same target-fixture cutoff when a feature snapshot is persisted. Historical RETRIEVED_AT_ONLY records remain useful as retrospective labels but are never retroactively certified as pre-match features.

## Derived pre-match feature set

The expanding dataset currently derives:

- Last-five points, goals for/against, goal difference and rest days
- Last-five shots on target/off target, attacks, dangerous attacks and possession
- First-half shots on target and dangerous attacks
- Corners, yellow cards and red cards
- Late goals for/against and substitutions from event timelines
- Per-team statistics/events coverage counts

Missing source statistics remain missing; they are not fabricated as zero. Feature coverage is reported with every dataset artifact.

The current prospective evaluator uses the hierarchical goal-rate model and does not yet consume the captured shot/possession/event features. Those features are retained for a later independently validated feature model. No xG, PPDA, lineup, injury or player-availability values are fabricated or currently claimed as ingested.

## Evaluation

The retrospective study separately scores 1X2, BTTS and Over/Under 2.5, with paired competition-stratified bootstrap confidence intervals and per-competition results. It is explicitly research-only.

The prospective evaluator uses expanding outer folds, inner chronological OOF Dixon-Coles rho estimation, a hierarchical Poisson model and a data-smoothed competition-only Poisson baseline. It separately evaluates 1X2, BTTS and Over/Under 2.5. The full dataset artifact and source lineage are archived alongside the evaluation report.

## Historical season limits and request budget

The manual season-history workflow probes the provider entitlement before import. It is capped at eight requests per competition and paces requests account-wide at one per minute. The provider's public documentation describes a three-month history window on Free, twelve months on Pro and deeper history on Ultra; the account's actual entitlement must be read from the status response before expecting a 2025 backfill to succeed.

## Release lock

Production promotion, public prediction publication and value betting remain locked. No model release is eligible until prospective sample sizes, date coverage, calibration, ROI confidence bounds, odds coverage and bookmaker-relative 1X2 criteria are all independently satisfied.
