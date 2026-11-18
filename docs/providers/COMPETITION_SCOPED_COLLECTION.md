# Competition-scoped 5Dollar historical collection

**Purpose:** acquire independently represented competition histories for internal, non-commercial model development and validation.

## Guardrails

- Uses the existing 5DollarFootballAPI community credential and the existing Neon production database.
- Only competition IDs present in `FIVEDOLLAR_COMMUNITY_APPROVAL.scope_values` are accepted.
- One competition per workflow run; workflow concurrency is serialized.
- Default window is 90 days, split into 7-day half-open windows.
- Default request ceiling is 20; the hard ceiling remains 40.
- Every HTTP page is durably reserved before the request, and its raw response, response hash, request event and checkpoint are persisted.
- A retry cannot repeat a reserved request. It must replay the captured response or stop for reconciliation.
- Historical retrievals remain `RETRIEVED_AT_ONLY`; no historical pre-match availability is inferred.
- Provider-local IDs remain separate. No aliases, canonical identity links, duplicate resolutions or review cases are automatically changed.
- Raw provider response bodies are retained internally and are not redistributed.
- No The Odds API credits are used.

## Approved additional competition scopes

The following IDs are already in the recorded non-commercial source approval. They are candidate acquisition scopes, not yet proof that each has been successfully fetched or independently represented in the database.

| Competition | Provider competition ID |
|---|---:|
| Brazil Serie A | `3118717965` |
| England Premier League | `4160026622` |
| France Ligue 1 | `3614399544` |
| Germany Bundesliga I | `686337048` |
| Italy Serie A | `3405541143` |
| Spain La Liga | `4212821298` |

Brazil Serie B (`522514093`) remains the original historical scope and is deliberately excluded from this candidate list.

## Execution

Open **Actions → 5Dollar competition-scoped historical import → Run workflow** on the validated feature branch.

Select exactly one competition ID. Keep the default 90-day boundaries and request budget of 20 for the first acquisition. The workflow uses the protected `veltrix-historical-import` environment, existing `VELTRIX_AI_ANALYST_DATABASE_URL` and existing 5Dollar community API secret. It does not print credentials.

The workflow requires the database secret to be configured in that environment. If the run stops because the secret or environment is unavailable, do not replace it with a new credential or a different database.

## After each run

1. Inspect the import run status, request reservations, raw response hashes, checkpoints and quarantine records.
2. The CLI automatically runs the competition-specific read-only validator after a completed import; preserve its JSON report and require `passed: true` before considering the records usable.
3. Verify the provider competition ID, season, date range, unique fixture IDs and team IDs.
4. Keep all canonical identity links in review until independently reconciled.
5. Update the research dataset manifest only after the source-level checks pass.

Do not start the next competition until the preceding run is completed and reconciled. A successful import does not itself establish point-in-time validity or prediction-model generalization.
