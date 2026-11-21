# VELTRIX model-version admission and database enforcement contract

**Status:** design contract; no migration has been applied.  
**Current state:** model quarantined, production predictions empty, value betting locked.

## 1. Two-tier model admission

Model identity and admission are separate concepts.

- `model_versions` stores one immutable model/config/training identity and its initial retrospective evaluation hash.
- `admission_tier` is `SHADOW` or `PUBLISHED`.
- `admission_status` is `ADMITTED` or `QUARANTINED`.
- A SHADOW-admitted version is visible only through the labelled RESEARCH ONLY feed.
- A PUBLISHED-admitted version additionally requires a prospective evaluation report and an explicit human sign-off event.
- A model version can never be re-admitted after quarantine. Quarantine is immediate and irreversible for that version.
- Promotion from SHADOW to PUBLISHED does not mutate the original config, training-data or retrospective evaluation hashes. It adds a separately hashed prospective report and a sign-off record. The tier can move SHADOW → PUBLISHED only once; it cannot move backward.
- Any change to training data, config/hyperparameters, feature definitions, inference code or probability generation creates a new model version and requires SHADOW admission again.

## 2. Model registry fields

Proposed `veltrix_ai_analyst.model_versions` fields:

- `model_version_id UUID PRIMARY KEY`
- `model_version TEXT UNIQUE NOT NULL`
- `model_family TEXT NOT NULL`
- `admission_tier TEXT NOT NULL CHECK IN ('SHADOW','PUBLISHED')`
- `admission_status TEXT NOT NULL CHECK IN ('ADMITTED','QUARANTINED')`
- `config_sha256 CHAR(64) NOT NULL`
- `training_data_sha256 CHAR(64) NOT NULL`
- `evaluation_report_sha256 CHAR(64) NOT NULL`
- `code_commit CHAR(40) NOT NULL`
- `artifact_sha256 CHAR(64) NOT NULL`
- `prospective_report_sha256 CHAR(64)`
- `signoff_actor TEXT`, `signoff_at TIMESTAMPTZ`, `signoff_reference TEXT`
- `admitted_at TIMESTAMPTZ NOT NULL`, `quarantined_at TIMESTAMPTZ`, `created_at TIMESTAMPTZ NOT NULL`

PUBLISHED-tier checks require a prospective report hash and sign-off actor/time/reference. SHADOW rows must not claim prospective sign-off. Hashes are lowercase 64-character SHA-256 strings; code commit is a 40-character lowercase Git SHA.

The registry is independent of the legacy `model_artifacts` table. Existing model_artifact rows must not be mistaken for the current hierarchical shadow model: the two current DB rows are `attack-defence-poisson-v1` and `attack-defence-poisson-v2-nested-tuned`, each trained on 380 fixtures/20 provider teams. The current shadow run is `hierarchical-poisson-shadow-v1`, trained on 996 labels/136 teams, and has no matching model_artifacts row.

## 3. Immutable hashes and monotonic state

A BEFORE UPDATE trigger on `model_versions` must enforce:

- `config_sha256`, `training_data_sha256`, `evaluation_report_sha256`, `code_commit`, `artifact_sha256`, `model_family` and `model_version` never change after insertion/admission.
- `admission_status` may remain unchanged or transition `ADMITTED → QUARANTINED`; never `QUARANTINED → ADMITTED`.
- `admission_tier` may remain unchanged or transition `SHADOW → PUBLISHED` only when a valid prospective report hash and explicit sign-off are supplied. It cannot downgrade.
- Once populated, `prospective_report_sha256` and sign-off fields are immutable.
- Quarantine event timestamp and actor/reason are captured in an append-only event ledger; no event row may be updated or deleted.

A separate append-only `model_admission_events` table records `SHADOW_ADMITTED`, `PUBLISHED_ADMITTED` and `QUARANTINED` events with actor, reason, report hash, evidence reference and event timestamp.

## 4. Research-run binding

Alter `research_shadow_forecast_runs`:

- Add `model_version_id UUID NOT NULL REFERENCES model_versions(model_version_id)`.
- Retain `report_sha256 CHAR(64) NOT NULL`.
- BEFORE INSERT trigger loads the referenced model version and requires:
  - `admission_status='ADMITTED'`
  - `admission_tier='SHADOW'`
  - `report_sha256 = model_versions.evaluation_report_sha256`
  - run's `training_data_sha256` equals `model_versions.training_data_sha256`
  - run's `model_version` string equals the referenced model version
- A SHADOW run cannot be inserted for a quarantined version or a PUBLISHED-only version.
- The table remains append-only.
- The RESEARCH ONLY API reads through an admission-aware view that joins `model_versions` and filters current `admission_status='ADMITTED'` and `admission_tier='SHADOW'`.

This prevents the research ledger from becoming a parallel admission bypass.

## 5. Published-prediction binding

Alter `predictions`:

- Add `model_version_id UUID NOT NULL REFERENCES model_versions(model_version_id)`.
- Add `evaluation_report_sha256 CHAR(64) NOT NULL`.
- Keep existing model_artifact and feature-snapshot provenance where applicable.
- BEFORE INSERT trigger requires `admission_status='ADMITTED'`, `admission_tier='PUBLISHED'`, exact evaluation-report hash equality, and existing point-in-time/fixture/feature chronology checks.
- Existing publication event validation remains, but also requires the linked model version to remain admitted and PUBLISHED.
- `published_predictions` and `published_prediction_markets` views join to `model_versions` at read time and filter `admission_status='ADMITTED'`, `admission_tier='PUBLISHED'`.
- Quarantining a model version immediately hides its existing prediction rows from all API reads without deleting immutable history.

## 6. Controlled write boundary and role separation

- Create a non-login owner role for admission-controlled write functions.
- Create a least-privilege application login role for the API runtime. Do not use `neondb_owner` as the application connection role.
- Application role receives SELECT only on approved views and required lookup tables; no direct INSERT, UPDATE, DELETE or TRUNCATE on `predictions`, `research_shadow_forecast_runs`, `model_versions` or admission-event tables.
- Grant EXECUTE only on SECURITY DEFINER functions such as `write_shadow_forecast_run(...)` and `write_published_prediction(...)`.
- Functions set a fixed safe `search_path`, validate all model-version and report-hash checks, and perform inserts atomically.
- No API route or worker may bypass these functions with direct table writes.
- Revoke inherited/default privileges as well as explicit grants. Verify effective privileges with `has_table_privilege` and negative integration tests using the actual runtime role.
- Updating the Vercel runtime secret to the new restricted role is a separate manual deployment/configuration blocker; do not place credentials in source or ledger.

## 7. Backfill of existing rows

Current read-only production snapshot:

- `predictions`: 0 rows.
- `research_shadow_forecast_runs`: 1 row, status `SHADOW_FORECASTS_READY`, model_version `hierarchical-poisson-shadow-v1`, training fixture count 996, report hash `e34d6e3459301cbfc8692d90691b0b48572166f338cefd484c2def8850c60d93`, forecast count 25.
- The current run's model_version column is nullable at schema level and has no FK. report_sha256 is required but is not bound to a model registry row.
- The existing research-run table has append-only UPDATE/DELETE triggers but no INSERT admission trigger.
- `predictions` has a pre-match INSERT trigger but no model admission check.
- Visible table grants provide direct INSERT to `neondb_owner`; no dedicated restricted application role is present.

Migration must create a model_versions row for the existing hierarchical shadow version with `admission_tier='SHADOW'` and `admission_status='QUARANTINED'`, not admitted. Bind the existing run to that row and preserve its report hash. Do not infer or fabricate config hash: derive it from the immutable archived run/artifact with a documented canonical serialization and verify it before migration. The old run must remain hidden from research API reads because its model version is quarantined.

The two legacy attack-defence model_artifacts must not be relabelled as the current hierarchical model. They remain separate immutable artifacts.

## 8. Migration and verification sequence

1. Offline schema design and migration tests; no production writes.
2. Create registry/event tables, constraints, immutable-hash trigger and monotonic status/tier trigger.
3. Compute and independently verify the current shadow config hash; create quarantined registry row and bind the existing research run.
4. Add run/prediction admission triggers and controlled write functions.
5. Create restricted runtime role, verify effective grants, and run negative direct-INSERT tests.
6. Add admission-aware views; update API queries to use those views.
7. Test quarantine transition in a disposable Neon branch: existing shadow/published rows disappear from views immediately; immutable records remain.
8. Only after tests pass, apply migrations to production under the approved migration workflow. Rotate the Vercel runtime role/secret as a separately verified step.
9. Re-read DB constraints, triggers, privileges, view rows, API research feed and published feed. No model can be promoted by schema migration alone.

## 9. Required negative tests

- Insert shadow run with no model_version_id → rejected.
- Insert shadow run with nonexistent model version → FK rejection.
- Insert shadow run referencing QUARANTINED version → rejected.
- Insert shadow run referencing PUBLISHED tier → rejected.
- Insert shadow run with report hash mismatch → rejected.
- Insert published prediction referencing SHADOW tier → rejected.
- Insert published prediction referencing QUARANTINED version → rejected.
- Insert published prediction with mismatched evaluation hash → rejected.
- Direct INSERT by application role on forecast tables → permission denied.
- EXECUTE controlled writer with invalid hash/tier/status → rejected.
- Update any immutable hash after admission → rejected.
- Reverse QUARANTINED to ADMITTED → rejected.
- Downgrade PUBLISHED to SHADOW → rejected.
- Quarantine admitted model version → existing forecast rows disappear from both API views immediately.
- SHADOW-admitted model can never appear in the published predictions view.
- PUBLISHED admission without prospective report and explicit sign-off → rejected.

No database migration is authorized by this design document. Production remains quarantined until model admission and prospective certification independently pass.
