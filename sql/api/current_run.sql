-- File: sql/api/current_run.sql
-- Purpose: Resolve one current run and the seven-day comparator once per request.
-- Grain: one run.
-- Constructs: scalar subquery, ordered successful runs.
-- Business question: Which immutable batch does this response describe?
SELECT r.*, (SELECT p.run_id FROM analytics.analytics_runs p
 WHERE p.status='succeeded' AND p.as_of_date=r.as_of_date-7
 ORDER BY (p.run_type='current') DESC,p.completed_at DESC,p.run_id DESC LIMIT 1) AS prior_run_id
FROM analytics.v_current_run selected
JOIN analytics.analytics_runs r ON r.run_id=selected.run_id;
