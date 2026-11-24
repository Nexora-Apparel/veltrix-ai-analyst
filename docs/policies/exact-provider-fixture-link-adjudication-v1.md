# Exact provider fixture-link adjudication policy v1

## Purpose

The prospective pipeline needs a canonical fixture row and an auditable source link before a captured provider fixture can enter the research dataset. This policy permits deterministic verification of a **source-local** fixture link when the source identity and its supporting provenance are exact.

It does not claim that a provider's fixture facts are independently true in the real world. It does not merge fixtures across providers, infer team aliases, repair source data, or promote a forecast model.

## Preconditions

A fixture source link may receive `SOURCE_FIXTURE_LINK_REVIEWED` only when all checks pass:

1. The link method is `EXACT_PROVIDER_FIXTURE_ID`, and its composite foreign key binds it to the exact provider fixture row.
2. The source observation, sighting, response, payload hash, provider, source, fixture ID and rights approval agree; the provenance audit returns `PROVENANCE_VERIFIED`.
3. The provider response is successful (HTTP 2xx), and the source approval was effectively approved and within its validity interval at observation time.
4. The approval permits `FEATURE_ENGINEERING`, `MODEL_TRAINING` and `MODEL_VALIDATION`.
5. The canonical fixture copies the provider fixture's kickoff, status and score fields exactly.
6. The canonical competition, home team and away team are the exact canonical IDs from effective team and competition links whose statuses are `SOURCE_IDENTITY_REVIEWED` or `REAL_WORLD_IDENTITY_VERIFIED`.
7. Exactly one provider source link points to the canonical fixture. A second source is never attached by this policy.
8. No other fixture in the same canonical competition has the same ordered canonical home/away teams within 120 seconds of kickoff.

## Decisions

- All checks pass and no collision exists: append `SOURCE_FIXTURE_LINK_REVIEWED` and set the canonical fixture identity status to `VERIFIED`.
- A deterministic duplicate collision exists, or the materializer already marked the fixture identity as conflicted: append `CONFLICT` and set the canonical fixture identity status to `CONFLICT`.
- Any provenance, rights, canonical mapping or exact-facts check fails: do not append a decision. Leave the link pending and fail the daily upcoming-fixture readiness gate if it is scheduled and upcoming.
- An existing review event is never overwritten or superseded by this policy. Existing human or automated decisions remain authoritative.

Every decision is append-only. Its evidence hash covers the policy version, provider fixture identity, source observation/sighting/response IDs, payload digest, approval, canonical IDs, kickoff/status/score, mapping states and any collision IDs.

## Separation of concerns

- `SOURCE_FIXTURE_LINK_REVIEWED` means the exact provider row is safely linked to its own source-local canonical fixture.
- It does not mean the provider's schedule or result has been externally verified.
- It does not establish PIT eligibility. The prospective dataset builder independently enforces system-observed timestamps, cutoff chronology, source rights and feature lineage.
- It does not certify the model, authorize production publication, unlock Value Bet, or permit cross-provider deduplication.
- Conflicts remain excluded; no source observation, provider fixture, canonical team, canonical competition or historical event is deleted or rewritten.

## Operational boundary

The daily job runs only for the six allowlisted prospective 5DollarFootballAPI competition scopes. It preflights every scope before writing, executes in one serializable transaction, makes zero provider requests, and verifies that every upcoming scheduled fixture is either eligible or explicitly conflicted. Unresolved upcoming links abort the transaction and block Stage 6.
