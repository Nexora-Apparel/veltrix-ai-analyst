-- Bind each durable request reservation to the exact captured provider response.
ALTER TABLE veltrix_ai_analyst.import_request_reservations
    ADD COLUMN provider_response_id BIGINT
        REFERENCES veltrix_ai_analyst.provider_responses(id) ON DELETE RESTRICT;

-- Reconstruct the importer's exact canonical request payload. Only backfill
-- when one response event matches this reservation's exact window and page.
WITH candidates AS (
    SELECT
        r.import_run_id,
        r.request_key,
        COUNT(DISTINCT e.provider_response_id) AS response_count,
        MIN(e.provider_response_id) AS provider_response_id
    FROM veltrix_ai_analyst.import_request_reservations r
    JOIN veltrix_ai_analyst.provider_request_events e
      ON e.endpoint = r.endpoint
     AND e.request_params = jsonb_build_object(
         'start_time', EXTRACT(EPOCH FROM r.window_start)::BIGINT,
         'end_time', EXTRACT(EPOCH FROM r.window_end)::BIGINT,
         'status', 'all',
         'page', r.page_number,
         'per_page', 100
     )
     AND e.started_at >= r.reserved_at
     AND e.started_at <= r.reserved_at + INTERVAL '5 minutes'
     AND e.provider = '5DollarFootballAPI'
     AND e.source_id = '5dollarfootballapi'
     AND e.http_status = 200
     AND e.provider_response_id IS NOT NULL
    JOIN veltrix_ai_analyst.provider_responses p
      ON p.id = e.provider_response_id
     AND p.provider = e.provider
     AND p.source_id = e.source_id
     AND p.endpoint = e.endpoint
     AND p.request_params = e.request_params
     AND p.http_status = e.http_status
    GROUP BY r.import_run_id, r.request_key
)
UPDATE veltrix_ai_analyst.import_request_reservations r
SET provider_response_id = c.provider_response_id
FROM candidates c
WHERE r.import_run_id = c.import_run_id
  AND r.request_key = c.request_key
  AND c.response_count = 1;

ALTER TABLE veltrix_ai_analyst.import_request_reservations
    ADD CONSTRAINT import_request_reservations_response_unique
    UNIQUE (provider_response_id);
