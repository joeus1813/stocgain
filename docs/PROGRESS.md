# Implementation progress

| Phase | Status | Date | Verification summary | Known issues |
|---|---|---|---|---|
| 0 — Foundation | Complete | 2026-10-09 | Docker 29.8.2 and Compose 5.5.1; PostgreSQL 17.11 healthy; real API health reports database ok; 12 backend + 4 frontend tests and 1 browser test pass; lint/typecheck/OpenAPI pass | Existing PostgreSQL identifiers retained for compatibility |
| 1 — Schema and data | Complete | 2026-10-10 | 26 tables; deterministic small/standard loads; 18 DQ checks zero; 70 backend + 4 frontend tests; explicit standard acceptance passes | Two explained on-time calibration deviations; optional large deferred |
| 2 — SQL analytics | Complete | 2026-10-11 | 12 views, 15 analyses, 11 extractors; historical leakage tests and measured standard-data plans pass | Actual-model comparisons/performance deferred to Phase 3 as prescribed |
| 3 — Model engines | Complete | 2026-10-12 | 13 real model runs; golden/leakage/neutrality gates pass | Risk calibration advisory documented |
| 4 — Backend API | Complete | 2026-10-13 | 239 backend, 4 frontend, 2 browser tests; DQ/type/lint/OpenAPI pass | Scenario warm/cold targets missed and documented |
| 5 — Frontend foundations | Complete | 2026-10-13 | Shared formatting, shell, URL scope, states and types verified | Full Phase 8 accessibility audit not performed |
| 6 — Main pages | Complete | 2026-10-13 | Real-data P0/P1 pages; 11 production browser tests; final 3 regressions pass | Inherited model/calibration limitations |
| 7 — Scenario Lab | Functional checks pass; acceptance open | 2026-10-13 | Neutral/disruption/policy/reset/validation pass; 20 measured browser evaluations | p95 2.426 s exceeds 1.5 s target |
| 8–9 | Not started | — | None | Stage 4 not authorized; explicitly requested Methodology delivered within Stage 3 |

## 2026-10-09 verification and limitations

Exact commands and real outputs are summarized in root `IMPLEMENTATION_STATUS.md`.
Environment: macOS 15.6.1 arm64, Python 3.12.7, Node 22.23.3, uv 0.13.0.

- `make setup`: passed locked installation; npm reports known development advisories.
- `make db-up`: failed because Docker executable is absent.
- `make lint`, `make typecheck`, `make check-openapi`: passed.
- `backend/.venv/bin/pytest backend/tests/unit -q`: 11 passed, 0.34 s.
- `make test`: 11 passed, 1 failed, 0.50 s; actual PostgreSQL connectivity failure. No skipping.
- `make test-frontend`: 4 passed, 0.899 s (includes root-env regression).
- `npm run format:check --prefix frontend`: passed.
- Production build passed after the environment regression fix (379 ms compile, 1.267 s TypeScript, 252 ms static generation).
- `make verify`: failed at the unchanged real DB test (11 passed, 1 failed, 0.59 s); lint and type checks passed first.
- Real HTTP health: HTTP 200 with database unavailable, as required by docs/08 §3.1.
- `make e2e`: 1 failed, 5.3 s; actual page says API ok / Database unavailable. The required healthy-DB assertion remains intact.
- Independent review found a root .env caching bug; regression reproduced and fixed. Relative backend config paths remain a deferred minor before Phase 1 use.

No data generation, migrations, SQL semantics, query performance, or Docker image builds are claimed verified. Five high npm development advisory entries remain rooted in braces; ESLint 9 deprecation is constrained by plugin peer compatibility. MIT owner placeholder remains per spec.

Resume: install/start Docker Desktop, complete Phase 0 health/integration gate, then implement Phase 1, then Phase 2. Original design files are preserved in Git baseline e1e45fe; only docs/02 §9 is annotated to distinguish present commands from future full-project commands.

## 2026-10-09 Phase 0 completion addendum

The earlier blocked results above are retained as historical evidence. Docker Desktop is now reachable through its installed CLI after sandbox socket access was approved. `docker info` reported Server 29.8.2, 8 CPUs, 7.748 GiB RAM; `docker compose version` reported v5.5.1. `make db-up` pulled `postgres:17`, started the existing `stocksense` Compose project, and waited until its single DB container was healthy. SQLAlchemy `SELECT version()` returned PostgreSQL 17.11. The live API returned `{"status":"ok","database":"ok","analytics_ready":false,"current_run_id":null,"version":"1.0.0"}`. After the owner-directed rename, `make test` ran 12 backend and 4 frontend tests successfully. `make e2e` ran the real browser test: 1 passed (1.6 s). `make lint`, `make typecheck`, and `make check-openapi` passed after the rename. Database and Compose project identifiers remain `stocksense` to preserve the existing volume. Phase 0 is complete; Phase 1 may begin.

## 2026-10-09 Phase 1 partial checkpoint

Added revisions `0001`–`0004` for the specified 26 physical tables across `ops`, `analytics`, and `sim_truth`, with row-level constraints, FKs and indexes. Applied them to the existing project database and the empty test database. On the test database, `alembic downgrade base && alembic upgrade head` succeeded. Readback from the project database returned revision `0004` and 26 application tables. `backend/.venv/bin/pytest backend/tests/db/test_reference_schema.py -q` passed 3 PostgreSQL tests. `make schema-dump` generated `sql/schema/current.sql` from PostgreSQL 17.11; its 27 `CREATE TABLE` entries include the public Alembic version table, leaving 26 application tables. Added the generator preset config and independent seeded RNG streams, but no dataset has been generated or loaded.

After these changes, `make lint typecheck test check-openapi` passed: Ruff and formatting clean across 30 Python files, mypy clean across 21 source files, frontend ESLint/TypeScript clean, 16 backend tests passed (including 3 actual PostgreSQL schema tests), 4 frontend tests passed, and generated OpenAPI matched the committed copy.

**Known limitations:** The phase's SQLAlchemy model declarations, simulator, loader, 18 DQ checks, small/standard preset verification, calibration, and complete constraint suite are unfinished. Phase 2 has not started. No inventory reconciliation, point-in-time SQL, or analytical query result is claimed.

## 2026-10-10 · Phase 1 completed

Resumed a5158bb; preserved the four applied revisions and existing PostgreSQL databases/volumes. Implemented complete SQLAlchemy metadata, deterministic generator, transactional COPY loader, 18 DQ checks, calibration profile, reconciliation view and tests. Independent code review completed without remaining critical/important findings. Scope stops here; Phase 2 has not started, Stage 1 is not yet complete and Stage 2 is not ready.

`make lint typecheck test check-openapi` passed: 46 Python files formatted, mypy 31 source files clean, ESLint/TypeScript clean, 70 backend tests (6.23 s), 4 frontend tests (0.922 s), health OpenAPI drift clean. The separately run standard PostgreSQL test passed in 8.12 s. `make migrate seed PRESET=standard SEED=42 schema-dump` and the small seed workflow against the existing test DB passed, with all 18 checks returning zero and zero MVs to refresh. SQLAlchemy metadata matches PostgreSQL; all 27 schema-dump CREATE TABLE definitions are unchanged, including the Alembic table. Reconciliation is the sole added view; ERD unchanged.

Standard: 12 stores, 400 SKUs, 180 days; daily_sales, inventory_snapshots and latent_demand each 864,000 rows. Final generation 7.880 s; corrected real COPY + validation 31.233 s; same-checksum revalidation 8.840 s. Small actual first generation/load took 0.276/1.118 s, satisfying the 5/30 s targets; final idempotent workflow took 0.257/0.462 s. Machine: macOS 15.6.1 arm64, Python 3.12.7, PostgreSQL 17.11. Full supporting counts, checksum evidence, SQL calibration metrics and commands are in [PHASE1_VERIFICATION.md](PHASE1_VERIFICATION.md).

Known limitations: explained OTR/approximate supporting-volume deviations in DECISIONS_LOG; optional large generator deferred; existing frontend development dependency advisories unchanged. Future-row deletion/as-of pipeline isolation belongs to Phase 2 and is not claimed. No forecasting, business API or dashboard. No permission or manual intervention remains pending; corrected reload followed owner approval and a verified local backup. No remote Git action.


## 2026-10-11 · Phase 2 / Stage 1 completion

Resumed the preserved uncommitted implementation at 7a4db02. Historical supplier receipt regression initially failed and now passes after cutoff-bounded PO/receipt CTEs; overview KPI invariance also passes. Sparse-weekday fallback and competing current/backfill/failed/running run tests pass. Exactly 12 views, 15 analyses, 11 extractors, overview KPI SQL and EXPLAIN wrappers are implemented. Physical table definitions/ERD and four migrations are unchanged.

`make lint typecheck test check-openapi`: 116 backend passed, 2 model-run tests skipped, 2 standard tests deselected (8.60 s); 4 frontend passed (0.942 s); Ruff 51 files, mypy 31 source files, ESLint, TypeScript and OpenAPI all pass. Separate SQL group: 46 passed, 2 skipped (2.52 s). Historical suite after overview regression: 6 passed (1.52 s). `make migrate explain schema-dump` passes; final Q2 MV 282.110 ms vs ops 925.174 ms, refresh 1.694 s. Earlier 266.931/725.047 ms measurements are retained as historical observations, not guarantees.

Known limitations: two requires_run comparisons need actual Phase 3 model outputs; forecasting-output equality after future deletion cannot run until forecasting exists. Populated-model Q4/Q7/Q8 and full Q5 performance remain unverified. No Stage 2 implementation, UI, model accuracy or business-impact claim. Operational calibration advisories persist and are explained in PHASE2_VERIFICATION.md. No manual step pending; no remote action. Phase 2's SQL acceptance criteria and Stage 1 gate pass; later-model tests are explicitly deferred under the roadmap.

Final standard verification: `pytest backend/tests/db/test_standard_dataset.py -m slow -q` passed 2 tests in 13.94 s; `stocgain data validate` reported all 18 checks zero in 7.956 s. The 864,000-row dense tables/MV, stored checksum and all 12/15/11 SQL inventories were verified against PostgreSQL.

Standalone execution: all 15 files also passed `docker compose exec -T db psql -v ON_ERROR_STOP=1 -U stocksense -d stocksense` on standard data.

## 2026-10-12 · Phase 3 verification

Implemented forecasting, ADI/CV² patterns, uncertainty distributions, lane fallback, checkpoint risk, safety stock/ROP/targets, financial exposure, deterministic explanations/recommendations, rolling-origin backtest, scenarios and transactional analytics persistence. Preserved all operational data and migrations. Both deferred Stage 1 model comparisons now execute against real model results.

Actual commands: `make analytics` produced 12 backfill + 1 current succeeded run; 4,800 forecasts/risks/recommendations, 201,600 daily forecasts, 7,206 checkpoints and 72 evaluation rows. Eight historical origins, three models, two bases, all observed segments. Initial total 150.050 seconds; current run 45.861 seconds (backtest 29.867). Historical runs were refreshed after promotion-window review correction.

`make lint typecheck test check-openapi`: all passed; 183 backend tests in 13.61 seconds, 4 frontend tests in 0.970 seconds. Earlier complete coverage execution: 182 passed, analytics coverage 92%; subsequent added persisted-neutral test passes (4 pipeline tests, 3.97 seconds). `python backend/scripts/verify_models.py` verified all 4,800 neutral scenario positions against stored PostgreSQL rows, no numeric difference >1e-6 after specified storage serialization. Point-in-time deletion tests compare actual forecast summaries and daily outputs. Independent formula review found and fixed promotion-window and insufficient-history action issues.

Observed/latent WAPE: stocgain 0.5766/0.5586; naive28 0.5839/0.5740; seasonal7 0.7796/0.7680. These simulated results are not business-impact claims. Full measured rows in `docs/perf/raw/phase3_models.json`.

Known limitations: risk calibration exceeds heuristic ranges (727 critical, 331 high), documented in DECISIONS_LOG; scalar scenario evaluation 6.837 seconds exceeds API target and will be measured/optimized in Phase 4. Independence and right-censoring assumptions remain as specified. Docker Desktop stopped after the successful suite; daemon restart is underway before further database verification. Phase 3 implementation/acceptance checks passed; Phase 4 may begin once database access is restored.


## 2026-10-13 · Phase 4 / Stage 2 completion

Single-agent continuation preserved all interrupted work. All 16 required P0 endpoints now return actual PostgreSQL-backed, schema-valid responses on small and standard datasets. Required metadata, filters, six overview widgets, recommendations, risk list, four position routes and stateless scenarios are complete. P1 routes remain absent per the approved roadmap. Existing minimal six-KPI page is verified; no Stage 3 UI, deployment or remote work.

Final commands and real outputs: `make lint` passes Ruff/96-file formatting/ESLint; `make typecheck` passes mypy63 and TypeScript; `pytest backend/tests -m '' --cov=stocgain.analytics --cov-report=term-missing` **239 passed, zero skipped/deselected, 73.60 s, 92% analytics coverage**. `make test-frontend check-openapi`: 4 frontend passed (0.902 s), no schema/type drift. Browser command with existing `.tools/playwright`: 2 passed (2.5 s). `stocgain data validate`: all 18 checks zero (8.149 s). Final standard model readback confirms all 4,800 neutral snapshot comparisons and 13 runs; independent numerical, model-dependent SQL and historical leakage regressions execute.

Measured HTTP p95 from 20 warm requests each: overview summary225.043 ms, risk list24.888 ms, detail9.862 ms, projection81.889 ms, scenario1793.594 ms. First cold projection6431.645 ms includes full-precision baseline replay. Optimized neutral core1526.985 ms; scalar SciPy object construction/promotion scans removed, no changed assumptions. Scenario1.5s and cold3s targets remain gaps allowed to be documented by Phase4; all other warm endpoint targets pass. Standard current counts unchanged: 4,800 forecasts/risks/recommendations, 201,600 daily forecasts, 7,206 checkpoints, 72 evaluation rows. Calibration advisory and original model limitations remain. Full evidence: PHASE4_VERIFICATION and docs/perf/raw/stage2_*.

Stage 2 acceptance gates pass with those explicit performance/calibration limitations. Local checkpoint only; no push. No owner approval or manual step pending.

## 2026-10-13 · Phase 5 foundation gate

Owner authorized Stage 3, superseding the old no-frontend handoff restriction. Single-agent implementation on the existing branch. Shared shell, canonical design tokens, Inter/JetBrains fonts, provenance popover, URL filters and local storage, typed cancellable API client, run-keyed queries, shared states/table/KPI/status components and friendly error/404 routes added. `npm --prefix frontend run typecheck` and lint pass; frontend unit tests 13 passed (1.06 s); real browser foundation checks 2 passed (1.9 s), with 1440/1280 screenshots under screenshots/wip. PostgreSQL-backed health reports current run 14 ready. Screen-specific acceptance continues in Phase 6. Remaining foundation follow-up: full 20-case cross-language formatting fixture and final browser checks across all implemented routes; these are tracked for final acceptance, not claimed verified.

### Phase 5/6 verification follow-up
Shared cross-language formatting fixtures now pass: 20 Python cases (0.02 s), frontend 33 tests (1.75 s). Phase 6 P0 real browser KPI/risk sorting/pagination/back/heatmap workflows: 3 passed (5.7 s). Supplier API results match the existing PostgreSQL view; scoped summary, CSV contents and existing-engine sensitivity baseline: 3 integration tests passed (3.68 s). No model or database changes. Next.js typecheck passes. The TanStack Table component explicitly opts out of React Compiler memoization because the library's table instance is mutable; SQL still owns sort/page state. Supplier CSV browser testing exposed a missing Content-Disposition CORS exposure; fixed, rerun pending. Scenario Lab implementation follows after that gate.

### Phase 6 gate and Phase 7 continuation
Supplier detail/CSV browser test passed (2.2 s) after CORS filename fix. P0 browser workflows and supplier API/view equality checks passed as recorded above; proceed to Scenario Lab. Stage 2 engines are reused unchanged. Scenario browser run confirmed neutral Overview equality, disruption aggregate increase and higher-service policy tradeoff, then failed on a test selector matching Next.js's route-announcement alert in addition to the intended field error. Narrowed the selector; rerun remains required. Observed development-server disruption update 5,322 ms (server calculation 1,691 ms), above the 1.5-second target; this is not claimed as a met performance gate.

## 2026-10-13 · Stage 3 final checkpoint

The earlier pending CORS/scenario-selector reruns above are resolved. All six requested pages plus supplier detail, CSV and sensitivity are implemented. Final `make lint typecheck test-frontend check-openapi` passes (Ruff102, mypy67, 38 frontend tests/1.08 s); production build and Prettier pass. Production `npm --prefix frontend run e2e -- --workers=1`: 11 passed/35.3 s. Last action-label regression followed by risk/responsive browser tests: 3 passed/20.9 s. Actual screenshots at 1440/390 and responsive checks at 1440/1280/390 retained.

Comprehensive `make lint typecheck test check-openapi` initially stopped on one new API metadata failure (259 passed, 1 failed, 2 default slow deselections/47.20 s). After schema metadata/CSV contract fix, targeted Phase6/contracts/position API tests: 16 passed/11.57 s, including future supplier receipt isolation. Full backend suite not rerun after repair; retained evidence distinguishes initial failure from targeted success. Formatter Python cases: 20 passed/0.02 s. No prior-stage data regeneration or engine investigations repeated.

One full-scope production browser benchmark (20 distinct demand changes, warm model cache, includes 400 ms debounce and rendered results): median 2241.609 ms, p95 2425.842 ms. **docs/07 §10.4 AC5 is unmet; Phase 7 and Stage 3 are not fully accepted.** Functional checks pass. Remaining latency is documented rather than changing formulas, dropping debounce or undertaking excluded major Stage 2 optimization. No Stage 4, deployment or remote action. Full evidence, limitations and launch instructions: [STAGE3_VERIFICATION.md](STAGE3_VERIFICATION.md).
