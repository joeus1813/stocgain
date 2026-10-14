# Stage 2 / Phase 4 verification

Date: 2026-10-13 (America/New_York). Continued d2791a3 and preserved all interrupted changes. Python 3.12.7, PostgreSQL 17.11, Node 22.23.3, macOS arm64. Existing `stocksense` database/volume identifiers, 26 tables and four migrations remain unchanged. No remote Git or deployment actions.

## Delivered scope

All 16 required P0 endpoints: health, metadata, filters, six overview widgets, recommendations, risk positions, four position endpoints and stateless scenario evaluation. Each response has an explicit strict schema, numeric unit metadata and documented fields. Filters validate actual IDs; pagination retains full filtered totals; sort selectors are whitelisted and stable; unknown IDs and invalid assumptions produce the specified error envelope.

Each analytical request reads one successful run in one read-only PostgreSQL snapshot. History and purchase-order facts are cutoff-bounded. Scenario/projection calculations reuse the existing Phase 3 functions and full-precision run inputs. The two-entry cache is keyed by database and run ID; cache invalidation and neutral equivalence are tested. No purchase orders or scenarios are written.

P1 endpoints (CSV, sensitivity, supplier endpoints, evaluation panel endpoint) remain absent as allowed by the Phase 4 roadmap. Phase 3 evaluation rows remain in PostgreSQL. The already-started minimal six-KPI page is only the required Phase 4 vertical slice; no Phase 5+ UI work.

## Measured standard API workload

`python backend/scripts/bench_api.py`: every required route executed successfully against the standard 12-store × 400-SKU dataset. One first call plus 20 warm requests per route, live local HTTP. Full-scope nonneutral scenario uses +20% demand and +4 lead-time days, so these measurements are actual calculations rather than cached response reuse. A final neutral request confirmed 4,800 positions with identical baseline/scenario metrics and zero deltas.

| Endpoint | First call ms | Warm p95 ms |
|---|---:|---:|
| `/health` | 53.310 | 3.577 |
| `/meta` | 11.450 | 6.846 |
| `/filters` | 3.082 | 2.860 |
| `/overview/summary` | 344.005 | 225.043 |
| `/overview/risk-distribution` | 16.396 | 15.923 |
| `/overview/risk-trend` | 75.345 | 68.754 |
| `/overview/store-comparison` | 47.656 | 43.610 |
| `/overview/category-heatmap` | 11.505 | 11.160 |
| `/overview/top-products` | 8.466 | 6.894 |
| `/recommendations` | 22.078 | 15.266 |
| `/risk/positions` | 31.464 | 24.888 |
| `/positions/1/1` | 21.064 | 9.862 |
| `/positions/1/1/history` | 11.946 | 7.797 |
| `/positions/1/1/projection` | 6431.645 | 81.889 |
| `/positions/1/1/purchase-orders` | 41.103 | 23.832 |
| `/scenarios/evaluate` | 1648.844 | 1793.594 |

Source: `docs/perf/raw/phase4_api.json`. Scenario p95 1.794 s remains above the 1.5 s target; cold baseline replay (first projection) 6.432 s exceeds the 3 s cache-warmup target. All other warm endpoint classes meet their specified targets. The earlier 6.837 s neutral computation and the current nonneutral HTTP p95 are different workloads, so they are reported separately, not as a precise speedup ratio.

Profiling isolated frozen SciPy object/docstring construction and repeated full promotion scans. Removed that overhead while preserving the finite-sum shortage, distribution selection and rounding rules. Golden/independent numerical fixtures and actual stored-snapshot equivalence verify unchanged mathematics.

## Acceptance evidence

Final consolidated suite: 239 backend tests passed in 73.60 s (92% analytics coverage), 4 frontend tests, 2 live browser tests. Strict mypy63, Ruff96/ESLint/TypeScript and OpenAPI drift pass. All 18 DQ checks zero in 8.149 s. Final stored-neutral verification passed all 4,800 positions; neutral core computation was 1.527 s. Detailed commands are recorded in IMPLEMENTATION_STATUS.md and docs/PROGRESS.md. Supporting Phase 3 model counts and forecast metrics are in `docs/perf/raw/phase3_models.json`. The final full suite includes the normally excluded standard PostgreSQL tests; no model comparison test is skipped.

## Known limitations

- Scenario warm and cold-cache targets remain unmet, as above; Phase 4 explicitly permits measured/documented gaps.
- Critical 727 (15.15%), High 331 (6.90%), Moderate 322, Low 3,420. The 22.04% Critical+High share exceeds the simulation plausibility range; preserved and explained in DECISIONS_LOG rather than adjusting outputs.
- Specified independence, receipt right-censoring, category-level weekday and seasonal forecasting limitations remain.
- Full production frontend, optional P1 API features, deployment and authentication are outside this phase.
