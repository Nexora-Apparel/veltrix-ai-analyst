# Security Policy

VELTRIX AI ANALYST is a public source repository. Never commit API keys, access tokens, passwords, signing keys, private user records, production database URLs, or other secrets.

## Reporting

Do not publish exploit details or credentials in public issues. Report suspected vulnerabilities privately to the repository owner through GitHub's supported private vulnerability reporting process, where enabled.

## Development safeguards

- Read secrets from environment variables or a managed secret store.
- Keep local environment files out of Git.
- Do not log authorization headers, tokens, or sensitive payloads.
- Use least-privilege credentials and rotate any credential that may have been exposed.
- Treat provider data terms, rate limits, and licensing restrictions as mandatory.
