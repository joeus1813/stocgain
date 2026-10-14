-- File: sql/views/010_v_current_run.sql
-- Purpose: Latest successful current analytics run.
-- Grain: zero or one run.
-- Constructs: CTEs, joins and window/conditional aggregates per docs/04.
-- Business question: Which completed run is current?
DROP VIEW IF EXISTS analytics.v_current_run CASCADE;
CREATE VIEW analytics.v_current_run AS
SELECT run_id, as_of_date, model_version, completed_at
FROM analytics.analytics_runs
WHERE status = 'succeeded' AND run_type = 'current'
ORDER BY as_of_date DESC, completed_at DESC
LIMIT 1;
