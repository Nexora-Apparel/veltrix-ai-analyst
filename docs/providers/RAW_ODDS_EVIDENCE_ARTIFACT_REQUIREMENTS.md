# Raw Odds Evidence Artifact Requirements

## Purpose

A capture manifest is metadata about a provider response. It is not a substitute for the raw response bytes. A manifest-only archive can establish what a probe reported, but it cannot independently establish that the recorded response byte count and SHA-256 match the provider payload.

## Required contents for a qualifying capture artifact

Each single-fixture, single-request odds probe must retain:

1. `capture-manifest.json`: the typed prospective capture manifest, including request identity, timestamps, response status, byte count, response SHA-256, source tick bounds, rights approval reference and admission result.
2. `response-body.bin`: the exact HTTP response body bytes as received, without JSON reserialization, whitespace normalization, decompression/recompression or newline conversion.
3. `artifact-checksums.txt`: SHA-256 checksums for both files.
4. `README.txt`: endpoint path, HTTP method, fixture identifier, provider, request count, retry count, pagination status and a statement that credentials and authorization headers are excluded.

## Validation sequence

- Verify the ZIP/archive checksum against the separately recorded artifact checksum.
- Extract the raw response body without transforming it.
- Recompute the raw body byte count and SHA-256.
- Require exact equality with the manifest values.
- Decode UTF-8 and parse strict JSON, rejecting duplicate object keys and non-finite numeric constants.
- Run the manual dry-run validator using independently supplied fixture, competition, bookmaker, market, kickoff and decision-cutoff context.
- Preserve rejected artifacts and reason codes for audit; do not silently repair or rewrite provider evidence.

## Security and privacy

- Never include API keys, authorization headers, cookies, signed URLs or other credentials in artifacts.
- Keep raw provider payloads private and within approved retention and data-use terms.
- Do not publish or redistribute raw bookmaker odds.
- Do not upload raw evidence to public repositories.
- Store evidence only in an approved private artifact location with restricted access.

## Admission boundary

A manifest-only artifact is classified as `METADATA_ONLY`. It may support access/schema observations, but it must not be treated as raw-response-hash verified, quote-level validated, point-in-time admitted, CLV evidence or value-betting certification evidence.

A complete artifact is still not automatically PIT-eligible. Source timestamps, rights, fixture identity, cutoff timing and all validator checks must independently pass.
