# Data Pipeline

Stage 2 builds provider adapters behind the provider-neutral contracts in
`backend/app/providers/contracts.py`.

## Rules

- Keep provider-specific HTTP and payload parsing inside isolated adapters.
- Normalize data before it enters domain services or persistence.
- Preserve provider name, provider record ID, retrieval timestamp, and source
  update timestamp where available.
- Require timezone-aware timestamps; never silently interpret naive timestamps
  as UTC.
- Deduplicate using stable provider identity plus canonical entity mapping.
- Use incremental synchronization and bounded request windows.
- Respect provider terms, rate limits, and field-level provenance.
- Never commit API keys or credentials.
- Do not derive or store prediction probabilities in the ingestion layer.

Concrete provider integrations are not yet implemented. Each source must pass
schema, rights, quota, coverage, and data-quality review before activation.
