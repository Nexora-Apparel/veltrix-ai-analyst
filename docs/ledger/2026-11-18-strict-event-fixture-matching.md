# Strict Odds Event-to-Fixture Matching

**Date:** 2026-11-18  
**Status:** IMPLEMENTED FOR REVIEW; NOT CONNECTED TO INGESTION

## Purpose

The Odds API event ID is a provider-local identifier. It must never be treated as a canonical 5Dollar fixture ID. Before any market observation can be associated with a project fixture, the two provider records must be matched under deterministic identity rules.

## Matching contract

- Match home team to home team and away team to away team; reversed orientation is rejected.
- Normalize Unicode diacritics, case and punctuation only.
- Do not infer aliases, abbreviations, alternate transliterations or club equivalence.
- Require exactly one team-identity candidate whose timezone-aware kickoff is within five minutes.
- Return `NO_TEAM_MATCH`, `KICKOFF_OUTSIDE_TOLERANCE` or `AMBIGUOUS` without a fixture ID when the evidence is insufficient.
- Duplicate candidate fixtures are ambiguous even if they share the same team names and kickoff.
- Naive timestamps, missing IDs and malformed team names are hard errors.
- A successful match retains the external event ID and 5Dollar provider fixture ID separately.

## Scope and safety

This helper is deterministic and offline. It makes no provider calls, writes no database rows and activates no model feature. It is not a replacement for human review of canonical team identity. The five-minute tolerance is a conservative initial matching threshold and must be measured against actual provider kickoff drift before production use.

## Required next validation

After a one-sport event-catalogue artifact and an approved 5Dollar upcoming fixture catalogue are available, run a dry comparison and report:
- total events and fixtures examined;
- exact matches;
- no-team-match cases;
- kickoff mismatches and observed drift distribution;
- ambiguous candidates;
- unmatched fixture coverage.

No odds-market request should be made until at least one exact, unique event-to-fixture match is verified.
