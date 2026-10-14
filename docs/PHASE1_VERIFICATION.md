# stocgain Phase 1 verification — 2026-10-10

Phase 1 is complete. Phase 2 has not started. Stage 1 as a whole remains incomplete; Stage 2 is not ready.

Environment: macOS 15.6.1 arm64, Python 3.12.7, Node 22.23.3, uv 0.13.0, PostgreSQL 17.11 in the existing Docker Desktop Compose service. Timings are local observations, not business-performance claims.

## Delivered

- SQLAlchemy metadata for all 26 existing tables; migrations 0001–0004 preserved. PostgreSQL metadata comparison passes.
- Seeded catalog, promotions, demand, daily inventory/fulfillment simulation, burn-in, named events, CSV writer and manifest checksums.
- Transactional COPY loader with checksum/header validation, advisory lock, idempotent same-content loads, explicit replacement gate and rollback on quality failure.
- All 18 DQ checks; inventory reconciliation view required by Phase 1; calibration profile and repeatable view commands. No Phase 2 analytical views, pipeline extraction or analyses.
- Regression tests for retail price endings and reserved supplier-name collisions; real PostgreSQL constraints, corruption checks, rollback, dense coverage and standard acceptance.

## Commands actually executed

Commands used repository-local uv/Node on PATH and `UV_CACHE_DIR=/private/tmp/stocksense-uv-cache`; Docker CLI directory `/Applications/Docker.app/Contents/Resources/bin` was also on PATH. Database commands used approved local socket/TCP access.

| Command | Result |
|---|---|
| `make lint typecheck test check-openapi` | PASS: Ruff/format (46 files), ESLint, strict mypy (31 source files), TypeScript, 70 backend tests in 6.23 s; 4 frontend tests in 0.922 s; health OpenAPI drift clean. One slow standard test excluded here and run explicitly below. |
| `pytest backend/tests/db/test_standard_dataset.py -m slow -q` | PASS: actual standard database row counts, 180 distinct dates, stored checksum and all 18 checks (8.12 s final run). |
| `make migrate seed PRESET=standard SEED=42 schema-dump` | PASS: Alembic head, standard generation 7.880 s, same-content load/validation 8.840 s, separate validation 8.252 s; all 18 checks zero; one reconciliation view applied; zero materialized views available to refresh; actual schema exported. |
| `DATABASE_URL=…/stocksense_test make seed PRESET=small SEED=42` | PASS: generation 0.257 s; same-content load/validation 0.462 s; separate validation 0.432 s; all 18 checks zero. |
| `stocgain data load --path data/generated/standard --replace` | PASS: corrected dataset COPY + validation 31.233 s, all 18 checks zero, after explicit owner approval and verified backup. |
| Initial small generation/load | PASS: generation 0.276 s; actual COPY + validation 1.118 s, meeting <5 s / <30 s targets. |
| Independent standard seed-42 generation | PASS: 7.669 s and 7.775 s runs had identical CSV checksums; final 7.880 s run retained the same checksum. |
| `stocgain data profile` | PASS: actual calibration results below. |

The standard acceptance check reads the main database; ordinary DB tests use the existing `stocksense_test`. Tests mutate rows inside rolled-back transactions. No database/volume reset was used. Existing migration round-trip evidence is retained from checkpoint a5158bb; no destructive downgrade of populated databases was repeated.

## Dataset evidence

Standard: 12 stores × 400 SKUs × 180 days, 2026-04-04 through 2026-09-30. Seed 42, burn-in 35 days. The three dense tables each have 864,000 rows. Small has 3 stores × 60 SKUs × 120 days and 21,600 rows per dense table.

Standard content checksum: `752b9d2d9f29b702003d3e86496e48912e4df0f0e00b223ef47cc477422684ba`.

Small content checksum: `25bb3fa41fb7e0cc98f332947f6fbf61c874e7e800b3421bce1d0c52c8b3fa5a`.

The checksum covers CSV bytes. Provenance `generated_at` is excluded, so manifest timestamps may differ. Generated CSVs and backups remain ignored.

| Table | Actual standard rows |
|---|---:|
| calendar | 305 |
| daily_sales | 864,000 |
| inventory_adjustments | 5,802 |
| inventory_receipts | 55,583 |
| inventory_snapshots | 864,000 |
| latent_demand | 864,000 |
| product_categories | 8 |
| product_suppliers | 473 |
| products | 400 |
| promotion_products | 846 |
| promotions | 143 |
| purchase_order_lines | 55,415 |
| purchase_orders | 17,074 |
| regions | 4 |
| stores | 12 |
| supplier_store_lanes | 576 |
| suppliers | 48 |

`ops.dataset_manifest` has one provenance row. The eight analytics output tables remain empty.

## Calibration and historical integrity

| Statistic | Observed |
|---|---:|
| Out all day | 6.2318% |
| Sold out | 2.0678% |
| End-of-day in stock | 91.6781% |
| Median supplier on-time rate, 90 days | 0.977102 |
| Demo Plumbing supplier on-time rate, 90 days | 0.819355 |
| Mean PO lead time | 8.86716 days |
| Split or short-closed line share | 7.48534% |
| Gross margin | 36.7061% |
| Zero-sales position-days | 47.6302% |

All DQ error and warning counts are zero, including inventory equation, daily continuity, sales availability, receipt/order bounds, sourcing/lane coverage, promotion overlap, money, latent-demand and provenance checks. Historical operational facts end at the specified history end; receipts follow order dates; calendar covers burn-in and future plans. Future promotions are intentional. Phase 2's historical `:as_of` extraction/future-row deletion tests are not implemented or claimed here.

Two on-time calibration deviations and approximate supporting-volume deviations are explained in DECISIONS_LOG; exact fulfillment formulas were retained. Optional large generation is not implemented. Phase 1 review completed with no remaining critical/important finding after supplier-name and price fixes. Existing development-tool advisories remain; no new dependency was added. UI remains health-only; no forecast, recommendation, dashboard or business impact is claimed.

The corrected reload was backed up to ignored `data/backups/pre-phase1-corrected-reload.dump`; `pg_restore --list` verified readability. Owner approval was obtained after automatic approval review initially blocked replacement. Databases, schemas, volume identifiers and Git history were preserved.
