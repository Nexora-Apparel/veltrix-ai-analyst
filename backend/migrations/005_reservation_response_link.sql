-- Bind each durable request reservation to the exact captured provider response.
ALTER TABLE veltrix_ai_analyst.import_request_reservations
    ADD COLUMN provider_response_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT;

-- Safely backfill only reservations with exactly one matching response event.
-- Ambiguous or absent evidence remains NULL and is rejected by replay.
WITH candidates AS (
    SELECT
        r.import_run_id,
        r.request_key,
        COUNT(DISTINCT e.provider_response_id) AS response_count,
        MIN(e.provider_response_id) AS provider_response_id
    FROM veltrix_ai_analyst.import_request_reservations r
    JOIN veltrix_ai_analyst.provider_request_events e
      ON e.endpoint = r.endpoint
     AND e.request_params = (
         SELECT p.request_params
         FROM veltrix_ai_analyst.provider_responses p
         WHERE p.id = e.provider_response_id
     )
     AND e.started_at >= r.reserved_at
     AND e.provider = '5DollarFootballAPI'
     AND e.source_id = '5dollarfootballapi'
     AND e.provider_response_id IS NOT NULL
    GROUP BY r.import_run_id, r.request_key
)
UPDATE veltrix_ai_analyst.import_request_reservations r
SET provider_response_id = c.provider_response_id
FROM candidates c
WHERE r.import_run_id = c.import_run_id
  AND r.request_key = c.request_key
  AND c.response_count = 1;
