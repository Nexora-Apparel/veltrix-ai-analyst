-- Immutable prediction storage and explicit publication gate.
-- Public prediction views intentionally expose only fixture details and probabilities.

CREATE TABLE veltrix_ai_analyst.prediction_feature_snapshots (
    feature_snapshot_id TEXT PRIMARY KEY
        CHECK (length(btrim(feature_snapshot_id)) BETWEEN 1 AND 180),
    canonical_fixture_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_fixtures(id) ON DELETE RESTRICT,
    prediction_cutoff_at TIMESTAMPTZ NOT NULL,
    feature_schema_version TEXT NOT NULL CHECK (length(btrim(feature_schema_version)) > 0),
    snapshot_sha256 CHAR(64) NOT NULL CHECK (snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    features JSONB NOT NULL CHECK (jsonb_typeof(features) = 'object'),
    source_evidence JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(source_evidence) = 'array'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (feature_snapshot_id, canonical_fixture_id)
);

CREATE TABLE veltrix_ai_analyst.predictions (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_fixture_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.canonical_fixtures(id) ON DELETE RESTRICT,
    model_artifact_id TEXT NOT NULL
        REFERENCES veltrix_ai_analyst.model_artifacts(model_artifact_id) ON DELETE RESTRICT,
    feature_snapshot_id TEXT NOT NULL,
    feature_schema_version TEXT NOT NULL CHECK (length(btrim(feature_schema_version)) > 0),
    feature_snapshot_sha256 CHAR(64) NOT NULL
        CHECK (feature_snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    prediction_cutoff_at TIMESTAMPTZ NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    training_cutoff_at TIMESTAMPTZ NOT NULL,
    model_version TEXT NOT NULL CHECK (length(btrim(model_version)) > 0),
    code_commit TEXT NOT NULL CHECK (code_commit ~ '^[0-9a-f]{40}$'),
    config_sha256 CHAR(64) NOT NULL CHECK (config_sha256 ~ '^[0-9a-f]{64}$'),
    expected_home_goals DOUBLE PRECISION NOT NULL CHECK (expected_home_goals > 0),
    expected_away_goals DOUBLE PRECISION NOT NULL CHECK (expected_away_goals > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (feature_snapshot_id, canonical_fixture_id)
        REFERENCES veltrix_ai_analyst.prediction_feature_snapshots(
            feature_snapshot_id, canonical_fixture_id
        ) ON DELETE RESTRICT,
    CHECK (training_cutoff_at < prediction_cutoff_at),
    CHECK (prediction_cutoff_at <= generated_at)
);

CREATE INDEX predictions_fixture_cutoff_idx
    ON veltrix_ai_analyst.predictions(canonical_fixture_id, prediction_cutoff_at DESC);
CREATE INDEX predictions_artifact_idx
    ON veltrix_ai_analyst.predictions(model_artifact_id, generated_at DESC);

CREATE TABLE veltrix_ai_analyst.prediction_market_probabilities (
    prediction_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.predictions(prediction_id) ON DELETE RESTRICT,
    market TEXT NOT NULL CHECK (
        market IN ('1X2', 'BTTS', 'TOTALS_1_5', 'TOTALS_2_5', 'TOTALS_3_5')
    ),
    outcome TEXT NOT NULL CHECK (outcome IN ('HOME', 'DRAW', 'AWAY', 'YES', 'NO', 'OVER', 'UNDER')),
    probability DOUBLE PRECISION NOT NULL
        CHECK (probability >= 0.0 AND probability <= 1.0),
    PRIMARY KEY (prediction_id, market, outcome),
    CHECK (
        (market = '1X2' AND outcome IN ('HOME', 'DRAW', 'AWAY'))
        OR (market = 'BTTS' AND outcome IN ('YES', 'NO'))
        OR (market IN ('TOTALS_1_5', 'TOTALS_2_5', 'TOTALS_3_5')
            AND outcome IN ('OVER', 'UNDER'))
    )
);

CREATE TABLE veltrix_ai_analyst.prediction_publication_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    prediction_id UUID NOT NULL
        REFERENCES veltrix_ai_analyst.predictions(prediction_id) ON DELETE RESTRICT,
    decision TEXT NOT NULL CHECK (decision IN ('PUBLISHED', 'WITHDRAWN')),
    effective_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    actor_id TEXT NOT NULL CHECK (length(btrim(actor_id)) > 0),
    reason_code TEXT NOT NULL CHECK (length(btrim(reason_code)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX prediction_publication_events_latest_idx
    ON veltrix_ai_analyst.prediction_publication_events(
        prediction_id, effective_at DESC, id DESC
    );

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.enforce_prediction_feature_snapshot_pit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    fixture_kickoff TIMESTAMPTZ;
    evidence_item JSONB;
    feature_name TEXT;
    observation_id BIGINT;
    sighting_id BIGINT;
BEGIN
    SELECT kickoff_at INTO fixture_kickoff
    FROM veltrix_ai_analyst.canonical_fixtures
    WHERE id = NEW.canonical_fixture_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PREDICTION_SNAPSHOT_FIXTURE_NOT_FOUND';
    END IF;
    IF NEW.prediction_cutoff_at >= fixture_kickoff THEN
        RAISE EXCEPTION 'PREDICTION_SNAPSHOT_CUTOFF_NOT_BEFORE_KICKOFF';
    END IF;

    IF jsonb_object_length(NEW.features) > 0
       AND jsonb_array_length(NEW.source_evidence) = 0 THEN
        RAISE EXCEPTION 'PREDICTION_SNAPSHOT_FEATURE_EVIDENCE_REQUIRED';
    END IF;

    FOR evidence_item IN SELECT value FROM jsonb_array_elements(NEW.source_evidence)
    LOOP
        BEGIN
            observation_id := (evidence_item->>'source_observation_id')::BIGINT;
            sighting_id := (evidence_item->>'source_sighting_id')::BIGINT;
            feature_name := evidence_item->>'feature_key';
        EXCEPTION WHEN OTHERS THEN
            RAISE EXCEPTION 'PREDICTION_SNAPSHOT_EVIDENCE_SHAPE_INVALID';
        END;

        IF observation_id IS NULL OR sighting_id IS NULL
           OR feature_name IS NULL OR length(btrim(feature_name)) = 0
           OR NOT EXISTS (
               SELECT 1
               FROM veltrix_ai_analyst.canonical_fixture_sources source_link
               JOIN veltrix_ai_analyst.pre_match_feature_observations feature
                 ON feature.target_fixture_id = source_link.provider_fixture_row_id
               WHERE source_link.canonical_fixture_id = NEW.canonical_fixture_id
                 AND feature.source_observation_id = observation_id
                 AND feature.source_sighting_id = sighting_id
                 AND feature.feature_key = feature_name
                 AND feature.prediction_cutoff_at = NEW.prediction_cutoff_at
           ) THEN
            RAISE EXCEPTION 'PREDICTION_SNAPSHOT_EVIDENCE_NOT_PIT_ADMITTED';
        END IF;
    END LOOP;

    FOR feature_name IN SELECT jsonb_object_keys(NEW.features)
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM jsonb_array_elements(NEW.source_evidence) AS evidence(item)
            WHERE item->>'feature_key' = feature_name
        ) THEN
            RAISE EXCEPTION 'PREDICTION_SNAPSHOT_FEATURE_WITHOUT_LINEAGE';
        END IF;
    END LOOP;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prediction_feature_snapshot_pit_gate
    BEFORE INSERT ON veltrix_ai_analyst.prediction_feature_snapshots
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.enforce_prediction_feature_snapshot_pit();


CREATE OR REPLACE FUNCTION veltrix_ai_analyst.enforce_prediction_inference_prematch()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn$
DECLARE
    fixture_kickoff TIMESTAMPTZ;
    snapshot RECORD;
    artifact_row RECORD;
BEGIN
    SELECT kickoff_at INTO fixture_kickoff
    FROM veltrix_ai_analyst.canonical_fixtures
    WHERE id = NEW.canonical_fixture_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PREDICTION_FIXTURE_NOT_FOUND';
    END IF;

    SELECT feature_schema_version, snapshot_sha256, prediction_cutoff_at
    INTO snapshot
    FROM veltrix_ai_analyst.prediction_feature_snapshots
    WHERE feature_snapshot_id = NEW.feature_snapshot_id
      AND canonical_fixture_id = NEW.canonical_fixture_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PREDICTION_FEATURE_SNAPSHOT_NOT_FOUND';
    END IF;
    IF snapshot.snapshot_sha256 <> NEW.feature_snapshot_sha256
       OR snapshot.feature_schema_version <> NEW.feature_schema_version
       OR snapshot.prediction_cutoff_at <> NEW.prediction_cutoff_at THEN
        RAISE EXCEPTION 'PREDICTION_FEATURE_SNAPSHOT_MISMATCH';
    END IF;

    SELECT training_cutoff_at, point_in_time_certified, artifact
    INTO artifact_row
    FROM veltrix_ai_analyst.model_artifacts
    WHERE model_artifact_id = NEW.model_artifact_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PREDICTION_MODEL_ARTIFACT_NOT_FOUND';
    END IF;
    IF artifact_row.point_in_time_certified IS NOT TRUE
       OR artifact_row.artifact->>'deployment_status' <> 'PRODUCTION_APPROVED'
       OR artifact_row.training_cutoff_at <> NEW.training_cutoff_at THEN
        RAISE EXCEPTION 'PREDICTION_MODEL_NOT_PRODUCTION_APPROVED_AND_PIT_CERTIFIED';
    END IF;

    IF NEW.training_cutoff_at >= NEW.prediction_cutoff_at
       OR NEW.prediction_cutoff_at >= fixture_kickoff
       OR NEW.generated_at < NEW.prediction_cutoff_at
       OR NEW.generated_at >= fixture_kickoff THEN
        RAISE EXCEPTION 'PREDICTION_INFERENCE_OUTSIDE_PREMATCH_WINDOW';
    END IF;

    RETURN NEW;
END;
$fn$;

CREATE TRIGGER prediction_inference_prematch_gate
    BEFORE INSERT ON veltrix_ai_analyst.predictions
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.enforce_prediction_inference_prematch();

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.prevent_market_changes_after_publication()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM veltrix_ai_analyst.prediction_publication_events
        WHERE prediction_id = NEW.prediction_id
        ORDER BY effective_at DESC, id DESC
        LIMIT 1
    ) AND (
        SELECT decision
        FROM veltrix_ai_analyst.prediction_publication_events
        WHERE prediction_id = NEW.prediction_id
        ORDER BY effective_at DESC, id DESC
        LIMIT 1
    ) = 'PUBLISHED' THEN
        RAISE EXCEPTION 'PUBLISHED_PREDICTION_MARKETS_ARE_IMMUTABLE';
    END IF;
    RETURN NEW;
END;
$fn$;

CREATE TRIGGER prediction_market_publication_guard
    BEFORE INSERT ON veltrix_ai_analyst.prediction_market_probabilities
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.prevent_market_changes_after_publication();

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.enforce_prediction_publish_gate()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    prediction RECORD;
    fixture RECORD;
    artifact_row RECORD;
    market_count INTEGER;
    latest_decision TEXT;
BEGIN
    SELECT p.*, snapshot.snapshot_sha256 AS stored_snapshot_sha256,
           snapshot.prediction_cutoff_at AS stored_snapshot_cutoff,
           snapshot.feature_schema_version AS stored_feature_schema_version
    INTO prediction
    FROM veltrix_ai_analyst.predictions p
    JOIN veltrix_ai_analyst.prediction_feature_snapshots snapshot
      ON snapshot.feature_snapshot_id = p.feature_snapshot_id
     AND snapshot.canonical_fixture_id = p.canonical_fixture_id
    WHERE p.prediction_id = NEW.prediction_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PREDICTION_NOT_FOUND';
    END IF;

    SELECT decision INTO latest_decision
    FROM veltrix_ai_analyst.prediction_publication_events
    WHERE prediction_id = NEW.prediction_id
    ORDER BY effective_at DESC, id DESC
    LIMIT 1;

    IF NEW.decision = 'PUBLISHED' THEN
        IF latest_decision = 'PUBLISHED' THEN
            RAISE EXCEPTION 'PREDICTION_ALREADY_PUBLISHED';
        END IF;

        SELECT id, kickoff_at, identity_status, completeness_status
        INTO fixture
        FROM veltrix_ai_analyst.canonical_fixtures
        WHERE id = prediction.canonical_fixture_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'PREDICTION_FIXTURE_NOT_FOUND';
        END IF;
        IF fixture.identity_status <> 'VERIFIED'
           OR fixture.completeness_status <> 'RECONCILED' THEN
            RAISE EXCEPTION 'PREDICTION_FIXTURE_IDENTITY_NOT_VERIFIED';
        END IF;

        SELECT training_cutoff_at, point_in_time_certified, artifact
        INTO artifact_row
        FROM veltrix_ai_analyst.model_artifacts
        WHERE model_artifact_id = prediction.model_artifact_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'PREDICTION_MODEL_ARTIFACT_NOT_FOUND';
        END IF;
        IF artifact_row.point_in_time_certified IS NOT TRUE
           OR artifact_row.artifact->>'deployment_status' <> 'PRODUCTION_APPROVED'
           OR artifact_row.training_cutoff_at <> prediction.training_cutoff_at THEN
            RAISE EXCEPTION 'PREDICTION_MODEL_NOT_PRODUCTION_APPROVED_AND_PIT_CERTIFIED';
        END IF;

        IF prediction.feature_snapshot_sha256 <> prediction.stored_snapshot_sha256
           OR prediction.prediction_cutoff_at <> prediction.stored_snapshot_cutoff
           OR prediction.training_cutoff_at >= prediction.prediction_cutoff_at
           OR prediction.prediction_cutoff_at >= fixture.kickoff_at
           OR prediction.generated_at < prediction.prediction_cutoff_at
           OR prediction.generated_at >= fixture.kickoff_at
           OR NEW.effective_at >= fixture.kickoff_at THEN
            RAISE EXCEPTION 'PREDICTION_PREMATCH_CHRONOLOGY_OR_SNAPSHOT_INVALID';
        END IF;

        SELECT COUNT(*) INTO market_count
        FROM veltrix_ai_analyst.prediction_market_probabilities
        WHERE prediction_id = NEW.prediction_id;

        IF market_count <> 11
           OR NOT EXISTS (
               SELECT 1 FROM veltrix_ai_analyst.prediction_market_probabilities
               WHERE prediction_id = NEW.prediction_id AND market = '1X2'
               GROUP BY prediction_id, market
               HAVING COUNT(*) = 3 AND ABS(SUM(probability) - 1.0) <= 0.00000001
           )
           OR NOT EXISTS (
               SELECT 1 FROM veltrix_ai_analyst.prediction_market_probabilities
               WHERE prediction_id = NEW.prediction_id AND market = 'BTTS'
               GROUP BY prediction_id, market
               HAVING COUNT(*) = 2 AND ABS(SUM(probability) - 1.0) <= 0.00000001
           )
           OR (SELECT COUNT(*) FROM veltrix_ai_analyst.prediction_market_probabilities
               WHERE prediction_id = NEW.prediction_id
                 AND market IN ('TOTALS_1_5', 'TOTALS_2_5', 'TOTALS_3_5')) <> 6
           OR EXISTS (
               SELECT market
               FROM veltrix_ai_analyst.prediction_market_probabilities
               WHERE prediction_id = NEW.prediction_id
                 AND market IN ('TOTALS_1_5', 'TOTALS_2_5', 'TOTALS_3_5')
               GROUP BY market
               HAVING COUNT(*) <> 2 OR ABS(SUM(probability) - 1.0) > 0.00000001
           ) THEN
            RAISE EXCEPTION 'PREDICTION_MARKET_DISTRIBUTIONS_INCOMPLETE_OR_UNBALANCED';
        END IF;
    ELSE
        IF latest_decision IS DISTINCT FROM 'PUBLISHED' THEN
            RAISE EXCEPTION 'PREDICTION_NOT_CURRENTLY_PUBLISHED';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prediction_publication_gate
    BEFORE INSERT ON veltrix_ai_analyst.prediction_publication_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.enforce_prediction_publish_gate();

CREATE TRIGGER prediction_feature_snapshots_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.prediction_feature_snapshots
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();
CREATE TRIGGER predictions_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.predictions
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();
CREATE TRIGGER prediction_market_probabilities_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.prediction_market_probabilities
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();
CREATE TRIGGER prediction_publication_events_append_only
    BEFORE UPDATE OR DELETE ON veltrix_ai_analyst.prediction_publication_events
    FOR EACH ROW EXECUTE FUNCTION veltrix_ai_analyst.reject_immutable_history_mutation();

CREATE VIEW veltrix_ai_analyst.published_predictions AS
SELECT p.prediction_id, p.canonical_fixture_id, p.model_artifact_id,
       p.feature_snapshot_id, p.prediction_cutoff_at, p.generated_at,
       p.expected_home_goals, p.expected_away_goals,
       event.effective_at AS published_at
FROM veltrix_ai_analyst.predictions p
JOIN LATERAL (
    SELECT decision, effective_at
    FROM veltrix_ai_analyst.prediction_publication_events
    WHERE prediction_id = p.prediction_id
    ORDER BY effective_at DESC, id DESC
    LIMIT 1
) event ON event.decision = 'PUBLISHED';

CREATE VIEW veltrix_ai_analyst.published_prediction_markets AS
SELECT published.prediction_id, markets.market, markets.outcome, markets.probability
FROM veltrix_ai_analyst.published_predictions published
JOIN veltrix_ai_analyst.prediction_market_probabilities markets
  ON markets.prediction_id = published.prediction_id;
