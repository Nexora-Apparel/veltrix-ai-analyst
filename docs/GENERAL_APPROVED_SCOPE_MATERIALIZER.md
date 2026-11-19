# General approved-scope canonical materializer

## Purpose

`backend/scripts/materialize_approved_scopes.py` generalizes the canonical
source-local materialization path beyond the historical Brazil Série B run.
It enumerates currently effective competition-scoped approvals and delegates
each scope to the shared provenance-checked canonical planner/materializer.

The runner does not call any football-data provider. It does not resolve
real-world team/competition identity, deduplicate provider records, promote
PIT observations, create prediction features, or publish predictions.

## Default behavior: read-only

Run from `backend/`:

```bash
python scripts/materialize_approved_scopes.py
```

The default mode:
- Reads only approvals whose effective status is APPROVED and whose validity
  interval includes the database statement timestamp.
- Expands each approval's competition IDs into independent provider/source/
  competition scopes.
- Requires exact source observation, sighting, successful response, payload
  hash, and rights-approval provenance for every candidate entity.
- Checks score/status consistency and existing canonical mapping drift.
- Reports every scope as READY or BLOCKED without issuing provider requests or
  writing database rows.
- Returns nonzero when no approved scopes are found or any scope is blocked.

To preview one exact scope, provide all three selectors:
`--provider`, `--source-id`, and `--competition-id`. Partial selectors fail
closed.

## Guarded write mode

A write is limited to one exact approved competition scope. It requires:
1. `--execute`.
2. All three exact scope selectors.
3. Environment variable
   `CANONICAL_MATERIALIZATION_CONFIRMATION=APPLY_ONE_APPROVED_CANONICAL_SCOPE`.
4. Database name exactly `veltrix_ai_analyst`.
5. An effective, currently valid source approval and a fresh ready plan.

Each scope is processed in a SERIALIZABLE transaction with a transaction-scoped
advisory lock, bounded lock/statement timeouts, provenance revalidation, and
post-write idempotency checks in the shared materializer. Existing canonical
mappings that differ from source evidence fail closed.

The GitHub Actions workflow
`.github/workflows/materialize-approved-canonical-scope.yml` provides:
- `preview`: read-only plan across every effective approved scope, optionally
  narrowed to one exact scope.
- `apply`: one exact scope only, with a separate typed confirmation and the
  protected `veltrix-historical-import` environment.

## Identity and PIT boundaries

Canonical entities created by this process remain source-local placeholders.
Provider identity links remain `REVIEW_REQUIRED`; fixture identity remains
`IDENTITY_REVIEW_REQUIRED` or `CONFLICT` when a narrowly evidenced collision
rule is configured; completeness remains `SOURCE_ROW_ONLY`. The materializer
does not merge aliases or deduplicate fixture rows.

The Brazil Série B America provider-ID alias pair is configured only on its
specific historical scope. Generic scopes do not inherit that special-case
identity assertion. Exact repeated ordered provider-team pairings within the
configured collision window are flagged as conflicts rather than merged.

All observations remain outside pre-match features unless independent PIT
publication/availability timestamps satisfy the strict kickoff cutoff.
Materialization does not make any observation PIT-certifiable.

## Launch sequence constraint

This runner is code-only until the guarded production migration gate is
completed and verified. Do not execute it against production before the
required migration set is applied through the checksum-verified workflow.
