# VELTRIX AI ANALYST — First-launch operations runbook
**Updated:** 18 November 2026

## Current production state

- API: `https://veltrix-ai-analyst-api.vercel.app`
- Vercel production deployment: `READY`
- `GET /health`: HTTP 200
- `GET /ready`: HTTP 503, database connected, migrations pending
- `GET /v1/predictions`: HTTP 503, fail-closed until prediction storage is migrated and eligible forecasts exist
- Neon project: `young-wind-27772160`
- Database: `veltrix_ai_analyst`
- Production migrations currently applied: 001–011
- Pending production migrations: 012–014

Production evidence inventory at the last inspection:
- 998 provider fixtures
- 384 canonical fixtures
- 115 captured provider responses
- 1,243 source observations
- 2,884 source-observation sightings
- 0 pre-match feature observations
- 0 point-in-time-certified observations

The existing model artifacts remain research-only. No public predictions or value bets may be published from them.

## 1. Secure migration credential

The Vercel `DATABASE_URL` and GitHub Actions database secret are separate settings. The Vercel variable is already configured and has been verified by the live `/ready` endpoint.

The guarded migration workflow reads this GitHub Actions environment secret:

- Environment: `veltrix-historical-import`
- Secret name: `VELTRIX_AI_ANALYST_DATABASE_URL`
- Value: the existing Neon production connection string for database `veltrix_ai_analyst`

Do not paste the connection string into chat, a commit, workflow output, or an unencrypted repository variable. If the GitHub environment secret already exists, do not replace it.

## 2. Apply production migrations

GitHub repository: `Nexora-Apparel/veltrix-ai-analyst`

1. Open **Actions**.
2. Select **Apply checksum-verified database migrations**.
3. Choose **Run workflow** on `main`.
4. Set `confirm_migrations` to `APPLY_CHECKSUM_VERIFIED_MIGRATIONS`.
5. Run the workflow and inspect its final verification output.

The workflow invokes the repository migration runner with the expected database name and explicit remote-database opt-in. It checks migration checksums, schema objects, target-fixture PIT constraints, publication storage, historical row preservation, and confirms the schema migration publishes no predictions.

Do not use an ad-hoc SQL editor to apply migrations. The same three migrations were already applied successfully to an isolated Neon branch (41 statements) and boundary-tested there. Production remains untouched until the guarded workflow runs.

## 3. Resume prospective data capture

The scheduled workflow is **VELTRIX prospective 5Dollar evidence capture**.

- Schedule: daily at 03:00 UTC (04:00 WAT).
- It uses a bounded rolling capture window and a request budget of four.
- It verifies the database name and required PIT migrations before making provider requests.
- It requires the approved 5Dollar provider credential in the `veltrix-historical-import` GitHub Actions environment. Accepted secret names are `FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY`, `FIVEDOLLARFOOTBALL_API_KEY`, or `FIVE_DOLLAR_FOOTBALL_API_KEY`.

Run it only after migrations 012 and 013 are verified. Check that it records real database-observed timestamps. Do not backfill historical records with invented observation times.

The Odds API is supplemental only. Preserve the user's stated remaining balance of 271 credits; no credits were spent in the current migration/readiness work.

## 4. Forecast admission and publication

Before the first forecast is published:

1. Capture genuine prospective source observations with exact response/sighting provenance.
2. Reconcile canonical fixture, team, and competition identity. Unverified or unresolved identities remain excluded.
3. Build target-bound pre-match features only from evidence available strictly before each target kickoff.
4. Create immutable feature snapshots with complete source lineage and matching hashes.
5. Train and evaluate models using chronological, point-in-time-safe data.
6. Promote only an artifact with an independently validated release manifest and `PRODUCTION_APPROVED` status.
7. Generate all five required markets: 1X2, BTTS, Over/Under 1.5, 2.5, and 3.5.
8. Publish through the database gate. The gate requires a PIT-certified, production-approved artifact, verified fixture identity, valid market distributions, and pre-match chronology.

A retrospective benchmark is research evidence only. It is not a substitute for prospective PIT certification.

## 5. Android first-device test

The Android debug build now embeds the production API base URL:

`https://veltrix-ai-analyst-api.vercel.app`

The V1 client:
- Shows 1X2 probabilities on Home.
- Shows BTTS Yes and No.
- Shows Over and Under for 1.5, 2.5, and 3.5.
- Distinguishes API failure from a valid empty prediction list.
- Keeps Value Bets locked until independent validation.

Install the CI-built debug APK on a physical Android device and verify startup, API connectivity, refresh, market display, empty state, unavailable state, and navigation. CI compilation is not a physical-device test.

## First-launch release gate

The product is not launch-ready until all of the following are true:

- [ ] Production migrations 012–014 applied and verified.
- [ ] `/ready` returns HTTP 200.
- [ ] Prospective capture is succeeding without PIT violations.
- [ ] A point-in-time-certified model release passes chronological validation.
- [ ] Real predictions are stored and published through the database gate.
- [ ] All five market distributions pass validation.
- [ ] Android physical-device test passes against the production API.
- [ ] Value betting remains disabled unless its separate certification criteria are met.

No fabricated probabilities, sample fixtures, or unverified performance claims are permitted in the first launch.
