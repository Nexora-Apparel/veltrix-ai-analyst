-- Keep feature snapshots immutable while recording later outcomes as append-only events.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM veltrix_ai_analyst.prospective_feature_snapshots
        WHERE label IS NOT NULL
           OR label_observed_at IS NOT NULL
           OR label_observation_id IS NOT NULL
           OR label_lineage IS NOT NULL
    ) THEN
        RAISE EXCEPTION
            'cannot split snapshot labels while populated inline labels exist';
    END IF;
END;
$$;

ALTER TABLE veltrix_ai_analyst.prospective_feature_snapshots
    DROP COLUMN label,
    DROP COLUMN label_observed_at,
    DROP COLUMN label_observation_id,
    DROP COLUMN label_lineage;

CREATE TABLE veltrix_ai_analyst.prospective_feature_snapshot_labels (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    snapshot_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.prospective_feature_snapshots(id),
    source_observation_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observations(id),
    source_sighting_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.source_observation_sightings(id),
    provider_response_id BIGINT NOT NULL
        REFERENCES veltrix_ai_analyst.provider_responses(id),
    label JSONB NOT NULL,
    label_observed_at TIMESTAMPTZ NOT NULL,
    label_lineage JSONB NOT NULL,
    label_sha256 CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT prospective_snapshot_labels_object
        CHECK (jsonb_typeof(label) = 'object'),
    CONSTRAINT prospective_snapshot_labels_lineage_object
        CHECK (jsonb_typeof(label_lineage) = 'object'),
    CONSTRAINT prospective_snapshot_labels_sha256
        CHECK (label_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT prospective_snapshot_labels_observation_unique
        UNIQUE (snapshot_id, source_observation_id)
);

CREATE INDEX prospective_snapshot_labels_chronology_idx
    ON veltrix_ai_analyst.prospective_feature_snapshot_labels
       (snapshot_id, label_observed_at, id);

CREATE OR REPLACE FUNCTION veltrix_ai_analyst.enforce_prospective_snapshot_label_timing()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    snapshot_kickoff TIMESTAMPTZ;
BEGIN
    SELECT kickoff_at
      INTO snapshot_kickoff
      FROM veltrix_ai_analyst.prospective_feature_snapshots
     WHERE id = NEW.snapshot_id
     FOR KEY SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'prospective feature snapshot does not exist';
    END IF;

    IF NEW.label_observed_at <= snapshot_kickoff THEN
        RAISE EXCEPTION 'outcome label must be observed strictly after kickoff';
    END IF;

    IF (NEW.label_lineage->>'availability_basis') IS DISTINCT FROM 'SYSTEM_OBSERVED_AT'
       OR (NEW.label_lineage->>'point_in_time_certifiable') IS DISTINCT FROM 'true'
       OR (NEW.label_lineage->>'rights_status') IS DISTINCT FROM 'APPROVED'
       OR COALESCE(NEW.label_lineage->>'rights_approval_id', '') = ''
       OR COALESCE(NEW.label_lineage->>'system_observed_at', '') = ''
       OR COALESCE(NEW.label_lineage->>'retrieved_at', '') = ''
       OR COALESCE(NEW.label_lineage->>'rights_valid_from', '') = ''
       OR COALESCE(NEW.label_lineage->>'payload_sha256', '') !~ '^[0-9a-f]{64}$'
       OR COALESCE(NEW.label_lineage->>'raw_response_sha256', '') !~ '^[0-9a-f]{64}$'
       OR NOT (
           COALESCE(
               NEW.label_lineage->'rights_permitted_uses',
               '[]'::jsonb
           ) @> '["MODEL_TRAINING","MODEL_VALIDATION"]'::jsonb
       )
       OR (NEW.label_lineage->>'source_observation_id') IS DISTINCT FROM NEW.source_observation_id::text
       OR (NEW.label_lineage->>'source_sighting_id') IS DISTINCT FROM NEW.source_sighting_id::text
       OR (NEW.label_lineage->>'provider_response_id') IS DISTINCT FROM NEW.provider_response_id::text
       OR (NEW.label_lineage->>'system_observed_at')::timestamptz IS DISTINCT FROM NEW.label_observed_at
       OR (NEW.label_lineage->>'retrieved_at')::timestamptz > NEW.label_observed_at
       OR (NEW.label_lineage->>'rights_valid_from')::timestamptz > NEW.label_observed_at
       OR (
           NEW.label_lineage->>'rights_valid_until' IS NOT NULL
           AND (NEW.label_lineage->>'rights_valid_until')::timestamptz <= NEW.label_observed_at
       ) THEN
        RAISE EXCEPTION
            'outcome label lineage is not PIT-certifiable or does not match source IDs';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prospective_snapshot_label_pit_guard
    BEFORE INSERT
    ON veltrix_ai_analyst.prospective_feature_snapshot_labels
    FOR EACH ROW
    EXECUTE FUNCTION veltrix_ai_analyst.enforce_prospective_snapshot_label_timing();

CREATE TRIGGER prospective_snapshot_labels_append_only
    BEFORE UPDATE OR DELETE
    ON veltrix_ai_analyst.prospective_feature_snapshot_labels
    FOR EACH ROW
    EXECUTE FUNCTION veltrix_ai_analyst.reject_prospective_snapshot_mutation();
