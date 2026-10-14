-- File: sql/api/forecast_evaluation.sql
-- Purpose: Persisted historical backtest measurements; no simulation truth read.
-- Grain: model-basis-segment.
-- Constructs: bound filters and stable ordering.
-- Business question: How accurate were held-out forecasts?
SELECT * FROM analytics.forecast_evaluations
WHERE run_id=:run_id AND segment_type=:segment_type
AND (CAST(:evaluation_basis AS text) IS NULL OR evaluation_basis=:evaluation_basis)
ORDER BY evaluation_basis,segment_value,model_name;
