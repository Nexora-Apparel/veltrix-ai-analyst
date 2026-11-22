# 2026-11-22 — owner-authorized research display enabled and production verified

## Authorization and scope

- User explicitly authorized the assistant to perform the owner-controlled production step.
- Enabled only the research shadow display switch in the Vercel production environment and deployed the already-reviewed `main` commit.
- No inference was triggered, no odds provider was called, no forecast/database rows were changed, no production prediction was published, and no Android UI or application source was modified.

## Environment change

- Vercel project: `veltrix-ai-analyst-api`
- Project ID: `prj_lweDbOPkWeoYieKXlKZSRzH5NFLk`
- Added `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED=true`
- Target: `production` only
- Type: `plain` (non-secret feature switch)
- Vercel environment variable ID: `hy0uzIXu1pgAE59z`
- The variable was absent before this authorized change.
- Existing admission record and model locks were not modified.

## Production deployment

- Deployment ID: `dpl_AWo5vpXMsxY1YrPQhT4ZuGnAdfqb`
- URL: `https://veltrix-ai-analyst-e3joktb0s-nexora-apparel.vercel.app`
- Production aliases include `https://veltrix-ai-analyst-api.vercel.app`
- Source commit: `c2ce6b604a042a4d09c4bf02b7861f5635374b3f`
- Branch: `main`
- Framework: FastAPI
- Build: successful; Vercel state `READY`.
- Build logs: Python 3.12 detected from `backend/pyproject.toml`; dependencies installed; Python bytecode compiled; build output completed and deployed.
- The live route returning forecasts proves the deployed admission file was present and passed `_model_admitted()`; otherwise the route would have returned `MODEL_QUARANTINED`.

## Post-deployment production HTTP verification

Requests were made directly to the production alias after the deployment reached `READY`.

### GET `/v1/research/predictions`

- HTTP `200`
- `status=SHADOW_FORECASTS_READY`
- `research_only=true`
- `research_label=RESEARCH ONLY`
- `certification=RETROSPECTIVE_NOT_PIT_CERTIFIED`
- `publication_status=NOT_PUBLISHED`
- `production_promotion=LOCKED`
- `value_betting=LOCKED`
- `model_version=hierarchical-poisson-newton-shadow-v2`
- `generated_at=2026-11-22T07:51:24.747189+00:00`
- `training_fixture_count=996`
- `predictions=21`
- This verifies that the production admission gate passed and the reviewed Stage 7 shadow run is now being served as research-only forecasts.

### GET `/v1/predictions`

- HTTP `200`
- `predictions=0`
- No research forecast was promoted into the published prediction endpoint.

## Fixture-level parity against the supervisor-reviewed Stage 7 artifact

All three selected fixtures appeared in the live production research response. Probabilities match the Stage 7 report values.

| Fixture | Home | Draw | Away | BTTS Yes | Over 2.5 |
|---|---:|---:|---:|---:|---:|
| Barcelona vs Villarreal | 85.1054% | 9.0615% | 5.8331% | 61.4421% | 84.5589% |
| Hull vs Brighton | 18.4762% | 24.2010% | 57.3228% | 45.7329% | 45.5686% |
| Liverpool vs Man Utd | 63.9183% | 20.1866% | 15.8951% | 52.9892% | 57.9275% |

- Live response contains 21 fixtures.
- The 21 forecast set and selected fixture probabilities match the previously reviewed Stage 7 output.
- No duplicate fixture issue was observed in the earlier reviewed artifact; this check focused on live count and three reference fixtures.

## Android integration status and qualification

- Repository source already calls `/v1/research/predictions` alongside published predictions and history.
- Home, BTTS, and Over/Under consume merged published + research fixture lists.
- Home shows a `RESEARCH ONLY` pill for research entries.
- The parser validates `research_only=true`, `publication_status=NOT_PUBLISHED`, `production_promotion=LOCKED`, and `value_betting=LOCKED`, then sets the local `researchOnly` flag. The pill is selected from this local flag; it does not bind the literal `research_label` response field.
- The parser still does not explicitly reject `MODEL_QUARANTINED` or `NO_RESEARCH_FORECASTS_AVAILABLE` based on `status`, nor validate `model_version`. This is a known app integration hardening item, deferred rather than changed under this authorization.
- Live API behavior is verified. Actual on-device Android rendering and installation of a build containing this integration were not performed or claimed.

## Safety invariants preserved

- Research label remains explicit.
- Certification remains `RETROSPECTIVE_NOT_PIT_CERTIFIED`.
- Publication status remains `NOT_PUBLISHED`.
- Production promotion remains `LOCKED`.
- Value betting remains `LOCKED`.
- Published predictions remain zero.
- No accuracy or profitability claim is made.
- No deferred model follow-up, Android code correction, automation, or new inference run was started.

## Next checkpoint

- Verify the existing Android build/runtime against the now-live endpoint and harden response status/model-version handling in a separate, reviewed change.
- Continue to keep production publication and value betting locked pending their independent certification gates.
