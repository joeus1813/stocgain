# 09 — Implementation Roadmap

**Audience:** OpenAI Codex (implementation agent) and the project owner reviewing progress.
**Related:** `AGENTS.md` (working rules), `CODEX_HANDOFF.md` (contract), `10_TEST_AND_QA_PLAN.md` (tests)

---

## 1. Principles

1. **One phase at a time.** A phase starts only when the previous phase's Definition of Done (DoD) is met and recorded in `docs/PROGRESS.md`.
2. **Vertical slices, real data.** From Phase 0 onward, the frontend talks to the real API, which reads the real database. No page is built against mock JSON. Test fixtures are allowed only inside test code.
3. **Verify, then claim.** A phase is done when its verification commands pass on a clean database. Record command output summaries (pass counts, timings) in `docs/PROGRESS.md`. Never record a result that wasn't observed.
4. **Small commits.** Commit per task group with messages `phase-N: <what>`.
5. **Scope discipline.** P0 first (Phases 0–7 core), P1 in Phases 6–8 only after P0 acceptance passes, P2 never without explicit instruction.

### 1.1 Dependency graph

```mermaid
flowchart LR
    P0[Phase 0<br/>Repo & environment] --> P1[Phase 1<br/>Schema & synthetic data]
    P1 --> P2[Phase 2<br/>SQL views & analyses]
    P2 --> P3[Phase 3<br/>Forecast, risk, recommendations]
    P3 --> P4[Phase 4<br/>Backend API]
    P4 --> P5[Phase 5<br/>Frontend foundations]
    P5 --> P6[Phase 6<br/>Overview, Risk Monitor, Detail, Suppliers]
    P4 --> P7[Phase 7<br/>Scenario Lab]
    P6 --> P7
    P6 --> P8[Phase 8<br/>Polish & performance]
    P7 --> P8
    P8 --> P9[Phase 9<br/>Docs & final verification]
```

### 1.2 Progress tracking file

Codex creates `docs/PROGRESS.md` in Phase 0 with this table and updates it at the end of every phase:

| Phase | Status | Date | Verification summary | Known issues |
|-------|--------|------|----------------------|--------------|

And `docs/DECISIONS_LOG.md` for implementation-level decisions (format: date, decision, reason, alternatives).

---

## Phase 0 — Repository and environment

**Objective:** A runnable skeleton where PostgreSQL, FastAPI, and Next.js start with documented commands and the browser shows a page that fetched `/api/v1/health` from the real API.

**Files/modules:** `Makefile`, `docker-compose.yml`, `docker/initdb/01_create_test_db.sql`, `.env.example`, `.gitignore`, `LICENSE` (MIT, copyright holder placeholder `<Project Owner>` for the owner to fill), `backend/pyproject.toml`, `backend/src/stocksense/{__init__,settings,logging_config,cli}.py`, `backend/src/stocksense/api/{app,deps,errors}.py`, `backend/src/stocksense/api/routers/health.py`, `backend/tests/unit/test_smoke.py`, `frontend/` (create-next-app with TypeScript, Tailwind, ESLint, App Router, `src/`), `frontend/src/app/page.tsx` (temporary health page), `docs/PROGRESS.md`, `docs/DECISIONS_LOG.md`.

**Tasks:**
1. Initialize git repository (if not already) and the directory structure from 02 §5.
2. Backend: `uv init`, add dependencies (02 §2), configure Ruff, mypy, pytest (markers `unit`, `db`, `api`).
3. `settings.py` with pydantic-settings reading `.env` (02 §8.1).
4. `create_app()` with CORS, request-ID middleware, error envelope handlers, `/api/v1/health` (returns DB status via `SELECT 1`).
5. `stocksense` Typer CLI with command groups `data`, `db`, `analytics`, `pipeline` (stubs that print "not implemented" and exit 2 are allowed only in this phase).
6. Docker Compose `db` service (Postgres 17, host port 5433, healthcheck, initdb script creating `stocksense_test`); `api`/`web` services under profile `full`.
7. Frontend: create Next.js app; install Tailwind v4, shadcn/ui init, TanStack Query, lucide-react, Recharts, TanStack Table; ESLint + Prettier; Vitest + RTL; Playwright (install browsers).
8. Temporary `page.tsx` calls `GET /api/v1/health` via TanStack Query and displays `status` and `database` (real request; this page is replaced in Phase 5).
9. Makefile targets from 02 §9.2 (those not yet functional print a clear message and exit non-zero).

**Dependencies:** Docker Desktop, uv, Node 22.

**Acceptance criteria:**
- `make setup && make db-up` succeeds on a clean clone.
- `make api` serves `http://localhost:8000/api/v1/health` → `{"status":"ok","database":"ok",...}`.
- `make web` serves `http://localhost:3000` showing "API: ok · Database: ok".
- `make lint typecheck test` pass (trivial tests).

**Verification commands:**
```bash
make setup && make db-up
curl -s localhost:8000/api/v1/health | python3 -m json.tool     # with make api running
make lint && make typecheck && make test
```

**Likely failure points:** port 5432/5433 conflicts (use `POSTGRES_HOST_PORT`); CORS misconfiguration; Tailwind v4 + shadcn init differences (follow current shadcn docs for Tailwind v4); Docker not running.

**Required tests:** `test_smoke.py` (app factory builds; health returns 200 with DB available); one Vitest test rendering a component.

**DoD:** All acceptance criteria pass; `PROGRESS.md` updated; no placeholder UI beyond the health page.

---

## Phase 1 — Database schema and synthetic data

**Objective:** Full schema migrated; deterministic generator produces the small and standard presets; loader populates the database; all data-quality checks pass.

**Files/modules:** `backend/src/stocksense/db/{engine,models,sql_loader}.py`, `backend/migrations/versions/0001…0004`, `backend/config/generator.toml`, `backend/src/stocksense/generator/*`, `backend/src/stocksense/loader/copy_loader.py`, `backend/src/stocksense/quality/checks.py`, `sql/quality/DQ01…DQ18*.sql`, `sql/views/100_v_inventory_reconciliation.sql` (needed by DQ01), tests in `backend/tests/unit/test_generator_*.py`, `backend/tests/db/test_constraints.py`, `backend/tests/db/test_data_quality.py`.

**Tasks:**
1. SQLAlchemy models for all 26 tables exactly as 03 §4–7 (types, nullability, CHECKs, FKs, unique and partial indexes, BRIN). Enums per 03 §2.
2. Alembic revisions 0001–0004 with working downgrades; verify `alembic upgrade head` and `alembic downgrade base` on an empty DB.
3. `stocksense db apply-views` (reads `sql/views/*.sql` in order; one transaction) and `stocksense db refresh` (refresh MVs).
4. Generator per 06: catalog, RNG streams, demand, promotions, simulation loop, fulfillment, events, writer with manifest and checksums. Vectorize the daily loop over positions with NumPy.
5. Loader: truncate + COPY in dependency order (03 §12) in one transaction; write manifest row; `ANALYZE`.
6. Quality runner: execute every `sql/quality/*.sql`, print a table (check, severity, violations), exit 1 on any error-severity violation.
7. `stocksense data profile` prints calibration statistics (06 §10).
8. `make seed PRESET=… SEED=…` wired: generate → load → apply views → validate → refresh.

**Acceptance criteria:**
- Small preset: generation < 5 s; load + validate < 30 s; all error checks 0 violations.
- Standard preset: 864,000 rows each in `daily_sales`, `inventory_snapshots`, `sim_truth.latent_demand`; all error checks 0 violations; warnings reviewed.
- Determinism: two generations with seed 42 have identical `content_checksum`.
- Calibration statistics within 06 §10 ranges (or deviations explained in `DECISIONS_LOG.md`).
- Constraint tests demonstrate rejections (negative stock, price ≤ cost, duplicate SKU, orphan FK, second primary supplier, invalid enum, PO promised ≤ order date).

**Verification commands:**
```bash
make db-reset
make seed PRESET=small SEED=42
make seed PRESET=standard SEED=42
uv run stocksense data validate
uv run stocksense data profile
uv run pytest -m "unit or db" -k "generator or constraints or data_quality" -q
psql "postgresql://stocksense:stocksense@localhost:5433/stocksense" -c "SELECT COUNT(*) FROM ops.daily_sales;"
```

**Likely failure points:** COPY column order mismatches (CSV header must equal table columns); timezone handling of dates; float rounding of money (use `Decimal` or round to 2 decimals before writing); slow Python loops (vectorize; target < 60 s standard); overlapping promotions; receipts after history end; burn-in POs referencing calendar dates (calendar must start at history_start − 35).

**Required tests:** all generator tests in 06 §11; constraint tests (10 §2); DQ tests (10 §3).

**DoD:** Acceptance criteria pass; ERD in 03 matches migrated schema (verify via `make schema-dump` diff review); `PROGRESS.md` updated with row counts and timings.

---

## Phase 2 — SQL analytics

**Objective:** All views, pipeline extraction queries, the 15 analyses, and API KPI SQL exist, run, and are tested.

**Files/modules:** `sql/views/010…120`, `sql/pipeline/*.sql`, `sql/analyses/01…15`, `sql/api/overview_summary.sql` (and stubs of other `sql/api/*.sql` written in Phase 4), `sql/explain/*.sql`, `backend/tests/db/test_views.py`, `backend/tests/db/test_sql_analyses.py`, `backend/tests/db/test_point_in_time.py`.

**Tasks:**
1. Implement views per 04 §3 exactly (semantics); `make migrate` applies them.
2. Implement pipeline extraction SQL per 04 §4 with `:as_of` parameters.
3. Implement analyses 01–15 per 04 §5 with header comments.
4. Implement `sql/api/overview_summary.sql` (04 §6.1) — it can be tested once Phase 3 writes a run; write the test now with `pytest.mark.requires_run` and enable it in Phase 3.
5. Write `sql/explain/` wrappers (executed in Phase 8).
6. A `stocksense db run-analysis 06` convenience command printing the result (useful for demos).

**Acceptance criteria:**
- Every view and analysis executes on small and standard presets.
- `v_inventory_reconciliation` has 0 discrepancies.
- Point-in-time test: for `as_of = history_end − 30`, deleting all rows dated after `as_of` (in a test transaction, rolled back) does not change any `sql/pipeline/*` result.
- Invariants listed per analysis in 04 §5 pass.
- `mv_daily_position` availability statuses match a Python recomputation on the small preset.

**Verification commands:**
```bash
make migrate
for f in sql/analyses/*.sql; do psql "$DATABASE_URL_PSQL" -f "$f" > /dev/null || echo "FAIL $f"; done
uv run pytest -m db -k "views or analyses or point_in_time" -q
```

(`DATABASE_URL_PSQL` = libpq form of the URL, documented in `.env.example`.)

**Likely failure points:** views depending on `v_current_run` returning empty before analytics exist (expected; tests for those run after Phase 3); FILTER clauses on window functions require PostgreSQL ≥ 9.4 (fine); `percentile_cont` returns double precision (cast to numeric before `ROUND`); date − integer arithmetic.

**Required tests:** 10 §4.

**DoD:** All SQL files present with headers; tests pass; `PROGRESS.md` updated.

---

## Phase 3 — Forecasting, lead time, risk, and recommendation engine

**Objective:** `make analytics` produces 12 backfill runs + 1 current run with evaluation; all outputs satisfy constraints and golden tests.

**Files/modules:** `backend/config/analytics.toml`, `backend/src/stocksense/analytics/{config,types,distributions,forecasting,demand_patterns,leadtime,risk,policy,exposure,explanations,replenishment,backtest,scenario,pipeline}.py`, `backend/tests/unit/test_{distributions,forecasting,leadtime,risk,policy,exposure,explanations,replenishment,backtest,properties,golden_cases}.py`, `backend/tests/fixtures/golden_cases.json`, `backend/tests/db/test_pipeline_outputs.py`.

**Tasks:**
1. `AnalyticsConfig` from `analytics.toml` (00 §4.2); frozen dataclass; JSON-serializable.
2. `distributions.py`: `select_family`, `prob_exceeds`, `quantile`, `expected_shortage`, `window_demand` (vectorized; 05 §5.2–5.3).
3. `forecasting.py`: day classification, EWMA level, fallbacks, variance floor, daily forecasts, horizon totals, trend ratio (05 §3). Operate on a dense `[positions × days]` matrix.
4. `demand_patterns.py`: ADI/CV² (05 §3.9).
5. `leadtime.py`: `select_lane_estimate`, `expected_arrival` (05 §4).
6. `risk.py`: checkpoints, probability, binding, expected shortage, days of cover, projection, tier, sensitivity (05 §5, §8).
7. `policy.py`: safety stock, reorder point, order-up-to, order quantity (05 §6).
8. `exposure.py` (05 §7); `explanations.py` (drivers, templates, shared number formatter; 05 §8.2–8.3); `replenishment.py` (rules, rationale, ranking; 05 §9).
9. `backtest.py`: rolling origins, three models, two bases, segments, metrics (05 §3.12).
10. `scenario.py`: assumption transform + aggregation (05 §10) — implemented now because it shares functions; exposed via API in Phase 7.
11. `pipeline.py`: create run row → extract (SQL) → forecast → lane estimates → risk → recommendations → (backtest if `--evaluate`) → bulk insert outputs (COPY or `executemany`) → mark succeeded; on exception mark failed. Delete older runs with same `(run_type, as_of_date)` after success.
12. CLI: `stocksense analytics run [--as-of DATE] [--evaluate]`, `stocksense analytics backfill --weeks N`; `make analytics`.

**Acceptance criteria:**
- Golden cases G1–G12 pass with tolerances from 05 §13.
- Property tests (05 §16.1 strict invariants) pass with Hypothesis-free randomized tests (fixed seeds) or explicit grids.
- Standard preset: `make analytics` completes; 13 succeeded runs; current run has 4,800 rows in `demand_forecasts`, `inventory_risk_snapshots`, `replenishment_recommendations`; 201,600 rows in `demand_forecast_daily`; evaluation rows for 3 models × 2 bases × all segments.
- All DB CHECK constraints satisfied (inserts succeed).
- Neutral scenario reproduces stored current-run outputs (per position, within 1e−6).
- Explanation numbers equal breakdown values for 100 random positions (string-level test using the formatter).
- `priority_rank` contiguous 1…N.
- Calibration of risk tiers within 06 §10 ranges or explained in `DECISIONS_LOG.md`.
- Pipeline time recorded in `analytics_runs.step_timings`; target < 3 minutes total for `make analytics` on standard (record actual).

**Verification commands:**
```bash
uv run pytest -m unit -q --cov=stocksense.analytics --cov-report=term-missing
make analytics
uv run pytest -m db -k pipeline -q
psql "$DATABASE_URL_PSQL" -c "SELECT run_type, COUNT(*) FROM analytics.analytics_runs WHERE status='succeeded' GROUP BY 1;"
psql "$DATABASE_URL_PSQL" -c "SELECT risk_tier, COUNT(*) FROM analytics.v_current_risk GROUP BY 1 ORDER BY 1 DESC;"
```

**Likely failure points:** leakage in backtest (DOW profile or chain rates computed with full history); off-by-one in window lengths (`w = ETA − T − 1`); NB parameterization (SciPy `nbinom(n, p)` with `p = μ/σ²`); count-family expected shortage for large `S`; NaN from 0/0 (CV with ℓ = 0); slow per-position Python loops (vectorize; checkpoints padded to max K); integer rounding (`ceil` on float error — apply `ceil(x − 1e−9)`); Decimal vs float when inserting.

**Required tests:** 10 §5–§6; analytics module line coverage ≥ 85%.

**DoD:** Acceptance criteria pass; `PROGRESS.md` includes the tier distribution and pipeline timings actually observed.

---

## Phase 4 — Backend API

**Objective:** All P0 endpoints (08 §2 #1–16, #22) implemented against the database with schemas, filters, pagination, sorting, errors, and tests. P1 endpoints may be stubbed **only** as absent routes (404), never as fake data.

**Files/modules:** `api/routers/{health,meta,filters,overview,recommendations,risk,positions,scenarios}.py`, `api/schemas/*`, `services/*`, `sql/api/*.sql`, `api/export_openapi.py`, `backend/tests/api/*`, `frontend/openapi.json`, `frontend/src/lib/api/schema.ts`.

**Tasks:**
1. `get_current_run` dependency; response headers.
2. Implement each endpoint per 08 §3 with SQL files per 04 §7 conventions (bound params, whitelisted sort).
3. Scenario endpoint wired to `analytics.scenario.evaluate` with run-keyed baseline cache (02 §13).
4. Error handlers and codes (08 §1.7).
5. OpenAPI export + TS generation; commit both.
6. API tests (10 §7).
7. **Vertical slice check:** replace the Phase 0 temporary page with a minimal page rendering the six Overview KPI values from `/overview/summary` (unstyled is fine) to confirm the end-to-end path before Phase 5.

**Acceptance criteria:**
- Every P0 endpoint returns schema-valid responses on small and standard presets.
- Consistency tests pass (08 §5).
- `make check-openapi` passes.
- p95 timings measured with a simple script (`backend/scripts/bench_api.py`, 20 requests per endpoint) and recorded; targets in 08 §1.8 met or gaps documented.

**Verification commands:**
```bash
uv run pytest -m api -q
make openapi && make check-openapi
uv run python backend/scripts/bench_api.py --base http://localhost:8000/api/v1
```

**Likely failure points:** array parameter binding (`CAST(:ids AS integer[])` with `None`); sort injection (whitelist only); Decimal serialization (configure Pydantic to serialize as float with rounding); slow scenario first call (warm cache on startup in a background thread or accept first-call cost and document).

**Required tests:** 10 §7.

**DoD:** Acceptance criteria pass; the minimal KPI page shows real numbers.

---

## Phase 5 — Frontend foundations

**Objective:** Design system, app shell, navigation, shared components, data hooks, and global states — production quality, connected to the real API.

**Files/modules:** `src/styles/globals.css` (tokens, 07 §3), `src/app/layout.tsx`, `src/components/layout/*`, `src/components/{kpi,charts,tables,risk,states}/*` (shared primitives), `src/lib/{format,url-state,constants,definitions}.ts`, `src/lib/api/{client,hooks,types}.ts`, `tests/unit/*`.

**Tasks:**
1. Tokens as CSS variables + Tailwind `@theme`; fonts via `next/font`.
2. `AppShell`, `Sidebar` (P1 nav items hidden until implemented), `TopBar` with as-of/run, `DatasetBadge` with provenance popover (from `/meta`), `FilterBar` (URL-synced, options from `/filters`).
3. `format.ts` implementing 07 §4.6 exactly, with unit tests including the 20 shared formatter fixtures (also used by backend tests: `backend/tests/fixtures/format_cases.json`, copied to `frontend/tests/fixtures/`).
4. `client.ts` error parsing into `ApiError`; hooks for each endpoint (query keys include filters and run ID).
5. Shared components (07 §12): KpiCard, RiskTierBadge, ProbabilityMeter, ActionChip, DataTable (manual sorting/pagination), ChartCard, EmptyState, ErrorState, AnalyticsNotReady, LoadingSkeleton.
6. `definitions.ts` with tooltip texts for every KPI/column (07 §4.3).
7. 404 and error routes.

**Acceptance criteria:**
- Shell renders on all routes with badge, as-of, and navigation; filters persist across navigation via URL.
- Formatter tests pass and match backend formatter fixtures.
- `AnalyticsNotReady` appears when the API returns 503 (verified by stopping analytics: `TRUNCATE analytics.analytics_runs CASCADE` on a test DB).
- `npm run lint`, `npm run typecheck`, `npm run test` pass.

**Verification commands:**
```bash
cd frontend && npm run lint && npm run typecheck && npm run test
```

**Likely failure points:** hydration mismatches from localStorage reads (read in `useEffect`); URL state loops; Tailwind v4 token mapping.

**DoD:** Acceptance criteria pass; visual review at 1440 and 1280 px recorded with screenshots in `docs/screenshots/wip/` (not final).

---

## Phase 6 — Main application pages

**Objective:** Overview, Risk Monitor, and Product Detail fully implemented (P0); Supplier Performance (P1) after P0 pages pass acceptance.

**Files/modules:** `src/app/page.tsx`, `src/app/risk/page.tsx`, `src/app/positions/[storeId]/[productId]/page.tsx`, `src/app/suppliers/*` (P1), feature components under `src/components/*`, backend P1 endpoints for suppliers (#18–20) when starting Suppliers, `tests/e2e/{overview,risk_monitor,product_detail}.spec.ts`.

**Tasks (P0):**
1. Overview per 07 §6 (all components, interactions, states).
2. Risk Monitor per 07 §7 (columns, filters, search, sort, pagination, URL state, row navigation, summary line).
3. Product Detail per 07 §8 (explanation, key numbers, projection chart, sales history chart, breakdown + checkpoints, POs, recommendation callout, copy summary).
4. E2E tests for these flows.

**Tasks (P1, after P0 acceptance):**
5. Supplier endpoints #18–20 and pages per 07 §9.
6. Sensitivity endpoint #17 and panel.
7. CSV export endpoint #12 and button.

**Acceptance criteria:** 07 §6.4, §7.4, §8.3 (P0); §9 (P1). E2E flows pass on standard dataset.

**Verification commands:**
```bash
make api & make web &
cd frontend && npx playwright test tests/e2e/overview.spec.ts tests/e2e/risk_monitor.spec.ts tests/e2e/product_detail.spec.ts
```

**Likely failure points:** Recharts SSR (render charts in client components only); chart performance with 56+28 points (fine); table re-render loops; date handling across time zones (treat API dates as plain dates, never `new Date('2026-09-30')` → UTC shift; use a date-only parser).

**DoD:** P0 acceptance criteria pass; no console errors; `PROGRESS.md` updated.

---

## Phase 7 — Scenario Lab

**Objective:** Interactive what-if simulator per 07 §10 using `POST /scenarios/evaluate`.

**Files/modules:** `src/app/scenarios/page.tsx`, `src/components/scenario/*`, `backend/tests/api/test_scenarios.py` (extend), `tests/e2e/scenario_lab.spec.ts`.

**Tasks:**
1. Controls with debounced auto-evaluation, request cancellation, URL state, reset.
2. Comparison grid, headline sentence, tier transition matrix, category chart, largest changes table, warnings, interpretation notes.
3. Presets (P1).
4. Tests: neutral scenario equality vs Overview; monotonic aggregate behavior for +lead time/+demand on standard; service-level tradeoff direction; reset; invalid input handling.

**Acceptance criteria:** 07 §10.4; scenario API tests (10 §6.3, §7).

**Verification commands:**
```bash
uv run pytest -m api -k scenario -q
cd frontend && npx playwright test tests/e2e/scenario_lab.spec.ts
```

**Likely failure points:** race conditions between slider changes (abort previous requests); float formatting of service level (0.95 vs 95); stale baseline cache after a new analytics run (cache keyed by run_id).

**DoD:** Acceptance criteria pass; timing of a full-scope evaluation recorded.

---

## Phase 8 — Production-quality polish

**Objective:** P1 features complete, performance measured, accessibility checked, no dead UI.

**Tasks:**
1. Methodology page (07 §11) with live parameters and forecast evaluation panel (#21).
2. Remaining P1 items: presets, advanced filters (supplier, action, below ROP), compact table toggle, "View data" chart tables.
3. Loading/empty/error state audit on every page (checklist in 10 §8.2).
4. Responsive audit at 1440, 1280, 1024, 768, 390.
5. `make explain`; write `docs/perf/QUERY_PERFORMANCE.md` with measured results; add indexes only with before/after evidence.
6. Accessibility: axe checks in Playwright on each page (0 serious/critical violations).
7. Dead-control audit: every button/link exercised by E2E or manual checklist.
8. Remove the hidden-nav guard once Suppliers is implemented.

**Acceptance criteria:** All P1 features in 01 §6.2 implemented or explicitly deferred in `PROGRESS.md` with reason; performance document contains real measurements; axe clean; responsive checks pass.

**Verification commands:**
```bash
make explain
make verify
make e2e
```

**DoD:** Acceptance criteria pass.

---

## Phase 9 — Documentation and final verification

**Objective:** A fresh clone reaches a populated dashboard with documented commands; the repository is portfolio-ready.

**Tasks:**
1. README per 11 §2 (overview, screenshots, architecture, ERD, SQL highlights, demo, provenance, decisions, testing, limitations, future work).
2. Capture **real** screenshots (Playwright script `frontend/scripts/screenshots.ts` at 1440 × 900) into `docs/screenshots/`.
3. `THIRD_PARTY_NOTICES.md` generated from dependency licenses (`uv pip list` + `npx license-checker --summary` or equivalent; no new runtime deps).
4. Clean-setup test: delete Docker volume and `data/generated`, fresh clone into a temp dir, follow README exactly, record total time.
5. Run `make verify` and `make e2e`; record results.
6. Update `docs/11_PORTFOLIO_AND_DEMO.md` "verified facts" section with measured numbers (row counts, runtimes, test counts) and finalize resume bullets using only verified facts.
7. Final review against `CODEX_HANDOFF.md` §14 acceptance checklist.

**Acceptance criteria:** CODEX_HANDOFF §14 checklist fully checked; README commands work verbatim; screenshots are of the running app.

**DoD:** Project owner can run the 3-minute demo (11 §4) end to end on a fresh setup.

---

## 2. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Generator too slow in Python | Medium | Medium | Vectorize daily loop; profile; small preset for tests |
| Simulation produces too few/many stockouts | Medium | High (demo quality) | Calibration ranges (06 §10); tune `β_p` range and event strength; record tuning |
| Backtest leakage | Medium | High (credibility) | Point-in-time functions; leakage test (10 §5.4) |
| Off-by-one window errors | High | High | Golden tests with explicit timing; projection vs checkpoint consistency tests |
| Scenario/pipeline divergence | Medium | High | Shared functions; neutrality test |
| Frontend/backend schema drift | Medium | Medium | Generated types; `check-openapi` |
| Over-polishing before correctness | Medium | High | Phase gates; P1 only after P0 |
| Version incompatibilities (Next/Tailwind/shadcn) | Medium | Low | Pin versions; follow current official setup guides; record in decisions log |
| Docker resource limits on laptop | Low | Medium | Postgres tuned modestly; standard preset sized for 8 GB+ machines |
| Misleading claims | Low | High | AGENTS.md rules; verified-facts section; provenance labels |

---

## 3. Global Definition of Done (project)

1. All P0 features (01 §6.1) implemented and verified; P1 features implemented or explicitly deferred with reason.
2. `make verify` and `make e2e` pass on a fresh setup.
3. No mock data in application code paths (`grep -R "mock\|faker\|lorem" frontend/src backend/src` returns nothing relevant).
4. Every displayed metric traceable per 04 §6.2.
5. Documentation updated to reflect what was built (including deviations).
6. Known limitations listed in README and Methodology page.
