# Prospective point-in-time evidence modes

## Purpose

Historical 5DollarFootballAPI backfill observations were retrieved after their original match kickoffs. They cannot be used to reconstruct what was known before those historical kickoffs. This document defines a separate, conservative route for future fixtures captured live.

## Accepted evidence modes

### 1. SOURCE_PUBLISHED_AT

Use when the provider supplies a verifiable publication timestamp for the exact payload.

Required:
- exact provider response and response ID
- exact payload hash and sighting
- source_published_at no later than retrieval
- available_at no earlier than source publication
- source publication and availability no later than prediction cutoff
- rights approved at cutoff and canonical identity verified

### 2. SYSTEM_OBSERVED_AT

Use when the provider does not expose publication time, but VELTRIX captures the exact response itself.

Required:
- exact successful provider response and response ID
- exact payload hash and sighting
- source_published_at must be NULL (do not fabricate it)
- available_at must equal the system retrieval timestamp exactly
- retrieval timestamp must be no later than prediction cutoff
- fixture kickoff must still be in the future at capture
- rights approved at cutoff and canonical identity verified

This proves only that VELTRIX had this exact payload by the recorded capture time. It does not prove when the provider originally published it.

## Historical boundary

- Existing observations and sightings are not backfilled, timestamped, or re-certified by migration 010.
- Existing historical observations remain non-PIT when their availability basis is retrieval-only.
- A SYSTEM_OBSERVED_AT sighting captured after a historical fixture's kickoff is rejected for any pre-kickoff prediction cutoff.
- Source event time, kickoff time, source update time, current provider projections and current web research are never substitutes for a pre-kickoff capture timestamp.
- The retrospective research report remains a non-PIT retrospective analysis until historical publication/availability evidence exists.

## Ingestion behavior

For each newly ingested fixture:
- if kickoff_at > retrieved_at, the exact fixture sighting is marked SYSTEM_OBSERVED_AT and PIT-certifiable for cutoffs at or after retrieved_at;
- otherwise it remains RETRIEVED_AT_ONLY and non-PIT-certifiable.

The database trigger independently enforces the timestamp rule. Application validation alone is not sufficient.

## Rights and commercial boundary

The current 5DollarFootballAPI approval permits internal analysis, feature engineering, model training, validation and public display with attribution, but does not permit commercial use or raw response redistribution. This pipeline does not change those terms. Do not commercialize the resulting data/model or redistribute raw provider responses without a new rights approval.
