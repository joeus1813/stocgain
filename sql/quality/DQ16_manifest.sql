-- File: sql/quality/DQ16_manifest.sql
-- Purpose: manifest
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT count(*) AS manifest_rows FROM ops.dataset_manifest HAVING count(*)<>1 OR count(*) FILTER(WHERE data_origin='synthetic')<>1;
