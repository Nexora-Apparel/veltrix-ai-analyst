# 2026-11-22 — production research-feed read-only gate check

## Scope and safety boundary

- User asked to proceed where possible with the post-approval research-feed checks.
- No environment variable was added or changed; no deployment/redeployment was triggered; no application code, prediction rows, publication rows, or Android UI was modified.
- The supervisor's prior owner gate remains in force: owner must enable `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED=true` and redeploy. This entry performs read-only inspection only.

## Production deployment and environment inspection

- Vercel project: `veltrix-ai-analyst-api`, project ID `prj_lweDbOPkWeoYieKXlKZSRzH5NFLk`.
- Latest production deployment: `dpl_DrExgyrWDbJQzAHQFAVCjenNiZBJ`, state `READY`, deployment URL `veltrix-ai-analyst-cdad4ens1-nexora-apparel.vercel.app`.
- Latest deployment source commit: `c2ce6b604a042a4d09c4bf02b7861f5635374b3f` (the ledger-only commit that records the supervisor decision); preceding production deployment is PR #148 merge `760eb0df0bd88fdd06eb105ab9b3c982db3fd70a`.
- Read-only production environment-variable listing (decrypted values disabled) returned only `DATABASE_URL`; `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED` is absent from the listed production variables. `hiddenProductionEnvCount=0`.
- This is the direct reason the route's owner display gate is not open.

## Actual production HTTP responses

Executed read-only GET requests from a temporary Vercel sandbox to the production API.

### GET /v1/research/predictions

- URL: `https://veltrix-ai-analyst-api.vercel.app/v1/research/predictions`
- HTTP status: `200`
- Exact body:
  ```json
  {"status":"MODEL_QUARANTINED","research_only":true,"research_label":"RESEARCH ONLY","certification":"RETROSPECTIVE_NOT_PIT_CERTIFIED","publication_status":"NOT_PUBLISHED","production_promotion":"LOCKED","value_betting":"LOCKED","generated_at":null,"training_fixture_count":0,"model_version":null,"predictions":[]}
  ```
- No research forecasts are currently being served. The HTTP 200 is the designed quarantine response, not a successful feed response.

### GET /v1/predictions

- URL: `https://veltrix-ai-analyst-api.vercel.app/v1/predictions`
- HTTP status: `200`
- Exact body:
  ```json
  {"predictions":[]}
  ```
- Published prediction list remains empty.

## Admission record / route diagnosis

- Current repository source at commit `c2ce6b604a042a4d09c4bf02b7861f5635374b3f` contains `backend/app/research/admissions/hierarchical-poisson-newton-shadow-v2.json`.
- Admission record fields inspected in source: model version matches `hierarchical-poisson-newton-shadow-v2`; tier `SHADOW`; certification `RETROSPECTIVE_NOT_PIT_CERTIFIED`; config SHA-256 `87063b2ddec253c65ce4071ce9e508d396c2ee5bb11b8dd85513dc97260d0698`; training SHA-256 `d70ee34940c8fc6681f3cd5751d4fdcc2e876b307fe388d9f3a792c73e34b262`; report SHA-256 `c724bb52677f3b93040028824ecc547f756e69c01586c7e9f9a587f75132f83d`; promotion and value betting locked; `app_display_enabled=false`.
- Route `backend/app/routes/research_predictions.py` requires BOTH the environment variable to equal the exact string `true` AND `_model_admitted()` to pass. The admission function intentionally requires `app_display_enabled=false` as a safe admission-record invariant; that field is not the blocker.
- Since the production environment listing does not contain `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED`, the first gate evaluates false and the route returns `MODEL_QUARANTINED`.
- Vercel's deployment file-tree endpoint returned 404 `File tree not found` for this deployment, so direct deployed-bundle file enumeration was unavailable. The admission file is confirmed in the exact deployed source commit's repository tree, but deployed-bundle presence is not independently certified by the file-tree API.

## Android app integration inspection (repository source)

- `PredictionApi.fetchUpcoming()` reads `/v1/predictions`.
- `PredictionApi.fetchResearchUpcoming()` reads `/v1/research/predictions`.
- `PredictionApi.fetchHistory()` reads `/v1/predictions/history`.
- `VeltrixDashboard` fetches all three feeds on initial load/refresh.
- Three screens consume merged published + research forecasts:
  - Home: displays merged fixture 1X2 probabilities and displays a literal `RESEARCH ONLY` pill for records whose local `researchOnly` property is true.
  - BTTS: displays merged BTTS Yes/No probabilities; it does not show a per-fixture research badge.
  - Over/Under: displays merged 1.5/2.5/3.5 goal probabilities; it does not show a per-fixture research badge.
- History remains sourced from published prediction history only. Value Bet remains locked with a static locked-state message.
- Badge binding qualification: the Android parser validates `research_only=true`, `publication_status=NOT_PUBLISHED`, `production_promotion=LOCKED`, and `value_betting=LOCKED`, then sets `researchOnly=true` locally. The Home pill text `RESEARCH ONLY` is selected from that local boolean. It does **not** read or bind the literal response field `research_label`. Therefore, the badge is guarded by the research-only boolean but is not directly bound to the response label field.
- Additional parser gap found: `parseResearchPredictions` does not check the response `status` or `model_version`. It accepts the current `MODEL_QUARANTINED` body as an empty research prediction list because the safety booleans/locks are present. The current UI consequently sees an empty feed rather than a distinct quarantine state; this should be recorded for a later approved app integration correction, not changed in this task.

## Fixture comparisons

- Production research response currently contains no fixtures, so Barcelona–Villarreal, Hull–Brighton, and Liverpool–Man Utd cannot be compared against the reviewed Stage 7 table.
- No forecast fixture is currently exposed through either production endpoint.

## Outcome

- Research display is not enabled in production.
- Published predictions remain zero.
- The owner-controlled environment/redeploy step is still the blocker.
- No deferred follow-up PR or automation work was started.
