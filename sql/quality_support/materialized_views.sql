-- File: sql/quality_support/materialized_views.sql
-- Purpose: Discover installed materialized views for explicit refresh.
-- Grain: one materialized view.
-- Constructs: PostgreSQL catalog query.
-- Business question: Which installed read models need refreshing?
SELECT matviewname FROM pg_matviews WHERE schemaname = 'analytics' ORDER BY matviewname;
