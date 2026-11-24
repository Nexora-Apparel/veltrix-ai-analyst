# Canonical fixture state-event policy v1

## Data model

A canonical fixture has two separate responsibilities:

- The canonical source link establishes which exact provider fixture ID the source-local canonical fixture represents.
- The canonical fixture's current status and score projection reflects the latest valid point-in-time observation for that provider fixture.

These are not the same fact. A fixture's identity link can remain stable while its state changes from scheduled to live to finished.

## Immutable evidence

The source observation and sighting tables remain the source of truth for captured provider responses. The append-only canonical fixture state-event table records the exact observation, sighting, provider response, source approval, payload hash, response hash, observed timestamp, kickoff, status and score used to update the current canonical fixture projection.

A state event is accepted only when:

1. The fixture source link is an exact provider-fixture-ID link and has an effective SOURCE_FIXTURE_LINK_REVIEWED decision.
2. The canonical fixture identity is VERIFIED, and the canonical team and competition mappings remain reviewed.
3. The latest source observation for the provider fixture matches the provider fixture projection exactly, including kickoff, competition, teams, status, score and provider record ID.
4. The sighting is SYSTEM_OBSERVED_AT, point-in-time certifiable, has available_at equal to system_observed_at, has no source-published timestamp, and is not observed before retrieval.
5. The provider response is successful and its fetched/system-observed timestamps and response hash match the sighting.
6. The source approval is effective and APPROVED at the observation timestamp, is scoped to the exact competition, and permits FEATURE_ENGINEERING, MODEL_TRAINING and MODEL_VALIDATION.
7. The event is strictly newer than the prior state event for that canonical fixture.

The database trigger validates these conditions and appends the event. A second trigger updates only the canonical fixture's current status and score projection from the event. The event itself cannot be updated or deleted.

## Dataset boundary

The prospective dataset builder requires both the reviewed canonical source-link audit and STATE_PROVENANCE_VERIFIED. A canonical fixture with stale or unsupported current state is excluded. A result observation does not rewrite the original schedule observation or the source identity link.

This state projection does not bypass prediction-cutoff checks, source rights, feature lineage, freshness limits, walk-forward certification, production publication locks or Value Bet locks.
