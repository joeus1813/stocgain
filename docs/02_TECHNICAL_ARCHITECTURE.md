# 02 — Technical Architecture

**Related:** `00_DESIGN_SUMMARY.md` (constants), `03_DATABASE_DESIGN.md`, `08_API_SPECIFICATION.md`, `09_IMPLEMENTATION_ROADMAP.md`

---

## 1. Architectural style

StockSense is a **modular monolith** made of three runtime units:

1. **PostgreSQL 17** — system of record for operational data, SQL views, and versioned analytics outputs.
2. **Backend** — one Python package (`stocksense`) that provides a CLI (data generation, loading, validation, analytics pipeline) and a FastAPI web application. Both share the same analytics modules.
3. **Frontend** — one Next.js (App Router, TypeScript) application.

There are no message queues, caches outside process memory, schedulers, or microservices. Analytics are computed in batch by an explicit command, stored in PostgreSQL, and read by the API.

---

## 2. Selected stack

Use current stable, mutually compatible versions at implementation time and pin exact versions in lockfiles (`uv.lock`, `package-lock.json`). The table lists the expected major versions.

| Layer | Technology | Expected version | Purpose |
|-------|------------|------------------|---------|
| Database | PostgreSQL | 17.x (Docker image `postgres:17`) | Relational storage, views, analytics SQL |
| Backend language | Python | 3.12 (≥ 3.11 supported) | API, pipeline, analytics |
| Package manager | uv | latest stable | Fast, reproducible Python environments |
| Web framework | FastAPI | latest stable 0.11x+ | REST API, OpenAPI generation |
| Validation | Pydantic | 2.x | Request/response schemas, settings |
| Settings | pydantic-settings | 2.x | Env-based configuration |
| ORM / SQL toolkit | SQLAlchemy | 2.0.x | Table models (migrations), Core `text()` for analytical SQL |
| Migrations | Alembic | 1.13+ | Versioned schema migrations |
| DB driver | psycopg | 3.2+ (`psycopg[binary]`) | Connections, fast `COPY` |
| Analytics | pandas 2.x, NumPy 2.x, SciPy 1.13+ | | Forecasting, distributions |
| CLI | Typer | latest stable | `stocksense` command |
| ASGI server | Uvicorn | latest stable | Serving FastAPI |
| Backend testing | pytest, pytest-cov, httpx | | Unit, DB, API tests |
| Backend quality | Ruff (lint + format), mypy (strict on `analytics/`) | | Static checks |
| Frontend framework | Next.js (App Router) | 15.x or current stable major | Pages, routing |
| UI runtime | React | 19.x | |
| Language | TypeScript | 5.x, `strict: true` | |
| Styling | Tailwind CSS | 4.x | Utility CSS + design tokens |
| Components | shadcn/ui (Radix primitives) | current CLI | Accessible primitives |
| Data fetching | TanStack Query | 5.x | Caching, loading/error states |
| Tables | TanStack Table | 8.x | Headless table logic (server-side sort/paging) |
| Charts | Recharts | 2.x or 3.x (latest stable) | Charts |
| Icons | lucide-react | latest | Icons |
| API types | openapi-typescript | 7.x | Generate TS types from OpenAPI |
| Frontend unit tests | Vitest + React Testing Library | | Component/unit tests |
| E2E tests | Playwright | latest | Smoke flows against running stack |
| Lint | ESLint (Next config) + Prettier | | |
| Containers | Docker Compose v2 | | Local infrastructure |
| Node | Node.js | 22 LTS | |

**Explicitly not used:** Redis, Celery, Airflow/Dagster/Prefect, Kafka, Kubernetes, GraphQL, Prisma/Drizzle (frontend does not touch the DB), Redux, D3 (directly), any paid service, any LLM API.

---

## 3. Architecture diagram

```mermaid
flowchart TB
    subgraph Browser["Browser — Next.js app (port 3000)"]
        Pages["Pages: Overview · Risk Monitor · Product Detail · Suppliers · Scenario Lab · Methodology"]
        RQ["TanStack Query hooks<br/>(typed from openapi.json)"]
        Pages --> RQ
    end

    subgraph API["FastAPI app (port 8000) — stocksense.api"]
        R["Routers /api/v1/*<br/>request validation, response models"]
        S["Services<br/>use-case orchestration, formatting of business objects"]
        Repo["Repositories<br/>execute named SQL files from sql/api/"]
        Scen["Scenario service<br/>calls stocksense.analytics.*"]
        Cache["In-process cache<br/>keyed by current run_id"]
        R --> S --> Repo
        S --> Scen --> Cache
    end

    subgraph CLI["stocksense CLI — batch pipeline"]
        Gen["generator/<br/>deterministic simulation"]
        Load["loader/<br/>COPY into ops + sim_truth"]
        DQ["quality/<br/>sql/quality/*.sql checks"]
        Views["db/views<br/>apply + refresh sql/views/*.sql"]
        Pipe["analytics/pipeline.py<br/>extract → forecast → lead time → risk → recommend → backtest"]
        Gen --> Load --> DQ --> Views --> Pipe
    end

    subgraph PG["PostgreSQL 17 (host port 5433)"]
        OPS[("ops.*<br/>dimensions + operational facts")]
        ANV[("analytics.v_* / mv_*<br/>SQL features & KPIs")]
        ANT[("analytics.* tables<br/>runs, forecasts, risk, recommendations, evaluations")]
        SIM[("sim_truth.*<br/>latent demand — evaluation only")]
    end

    RQ -- "HTTP JSON" --> R
    Repo --> ANV & ANT & OPS
    Cache -. "baseline inputs" .-> ANT
    Load --> OPS & SIM
    Views --> ANV
    Pipe -- "sql/pipeline/*.sql (as-of params)" --> ANV & OPS
    Pipe --> ANT
    Pipe -. "backtest only, labeled" .-> SIM
```

### 3.1 Layer responsibilities

| # | Layer | Responsibilities | Must NOT |
|---|-------|------------------|----------|
| 1 | Frontend presentation (`frontend/`) | Rendering, formatting numbers/dates, URL filter state, chart interactions, loading/empty/error states | Calculate business metrics; hold mock data; talk to the DB |
| 2 | REST API (`stocksense/api/`) | HTTP routing, request validation, pagination params, response schemas, error mapping, OpenAPI | Contain SQL strings or formulas |
| 3 | Business logic / recommendation (`stocksense/services/`, `stocksense/analytics/replenishment.py`, `explanations.py`) | Compose repository results into business objects; select current run; scenario orchestration; recommendation rules | Execute raw HTTP concerns |
| 4 | Forecasting & analytics (`stocksense/analytics/`) | Pure functions over NumPy/pandas: forecasting, distributions, lead time, risk, backtest, scenario math | Import FastAPI; open DB connections (except `pipeline.py` orchestrator) |
| 5 | Data layer (PostgreSQL + `stocksense/db/` + `sql/`) | Storage, integrity constraints, SQL views, analytical SQL, migrations | Contain Python-only logic |
| 6 | Synthetic data pipeline (`stocksense/generator/`, `loader/`, `quality/`) | Deterministic simulation, CSV output, COPY loading, data-quality checks | Read from analytics tables |

---

## 4. Path from raw data to dashboard metric

Example: **"Est. gross margin at risk" KPI on the Overview page.**

```mermaid
sequenceDiagram
    autonumber
    participant Gen as Generator
    participant DB as PostgreSQL
    participant Pipe as analytics pipeline
    participant API as FastAPI
    participant UI as Next.js
    Gen->>DB: COPY ops.daily_sales, inventory_snapshots, purchase_orders, lines, receipts, adjustments, promotions
    DB->>DB: data-quality checks (sql/quality/*.sql) — fail pipeline on violations
    DB->>DB: REFRESH MATERIALIZED VIEW analytics.mv_daily_position
    Pipe->>DB: sql/pipeline/extract_daily_history.sql (as_of)
    Pipe->>DB: sql/pipeline/extract_lane_lead_times.sql (as_of)
    Pipe->>DB: sql/pipeline/extract_open_po_lines.sql (as_of)
    Pipe->>Pipe: forecasting.py → daily forecasts, σ_d
    Pipe->>Pipe: risk.py → checkpoints → expected shortage units
    Pipe->>Pipe: exposure = shortage × lost-sale rate × (price − cost)
    Pipe->>DB: INSERT analytics.inventory_risk_snapshots (run_id)
    UI->>API: GET /api/v1/overview/summary?store_id=3
    API->>DB: sql/api/overview_summary.sql (current run_id, filters)
    DB-->>API: SUM(margin_at_risk_usd) ...
    API-->>UI: {"gross_margin_at_risk_usd": 48213.55, ...}
    UI->>UI: format "$48.2K", label "Est.", tooltip definition
```

---

## 5. Repository structure

```
StockSense/
├── AGENTS.md                       # coding-agent instructions
├── CODEX_HANDOFF.md                # consolidated implementation contract
├── README.md                       # written in Phase 9
├── LICENSE                         # MIT (Phase 0)
├── THIRD_PARTY_NOTICES.md          # dependency license summary (Phase 9)
├── Makefile                        # all developer commands
├── docker-compose.yml
├── docker/initdb/01_create_test_db.sql   # creates stocksense_test on first start
├── scripts/verify_fresh_setup.sh   # Phase 9 clean-clone verification
├── .env.example
├── .gitignore                      # includes data/generated/, .env, node_modules, .venv
├── data/
│   └── generated/                  # generator output (gitignored)
├── docs/
│   ├── 00_DESIGN_SUMMARY.md … 11_PORTFOLIO_AND_DEMO.md
│   ├── perf/QUERY_PERFORMANCE.md   # EXPLAIN ANALYZE results (Phase 8)
│   ├── screenshots/                # real screenshots (Phase 9)
│   ├── PROGRESS.md                 # phase status + real verification output (Codex)
│   └── DECISIONS_LOG.md            # implementation-time decisions by Codex
├── sql/
│   ├── views/                      # repeatable view definitions, applied in filename order (see 04 §3)
│   │   ├── 010_v_current_run.sql
│   │   ├── 020_mv_daily_position.sql
│   │   ├── 030_v_po_line_status.sql
│   │   ├── 040_v_po_status.sql
│   │   ├── 050_v_supplier_lane_performance.sql
│   │   ├── 060_v_supplier_performance.sql
│   │   ├── 070_v_category_dow_profile.sql
│   │   ├── 080_v_product_abc_class.sql
│   │   ├── 090_v_stockout_episodes.sql
│   │   ├── 100_v_inventory_reconciliation.sql
│   │   ├── 110_v_current_risk.sql
│   │   └── 120_v_risk_trend.sql
│   ├── analyses/                   # portfolio SQL analyses (01–15), runnable standalone
│   ├── pipeline/                   # as-of-parameterized feature extraction used by analytics
│   ├── api/                        # named queries used by API repositories
│   ├── quality/                    # data-quality checks (each returns violating rows)
│   ├── explain/                    # EXPLAIN (ANALYZE, BUFFERS) scripts for key queries
│   └── schema/ddl_reference.sql    # generated by `make schema-dump` (not hand-edited)
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── config/
│   │   ├── analytics.toml          # model parameters (see 00 §4.2)
│   │   └── generator.toml          # presets + demo narrative events
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/               # 0001_… 0004_…
│   ├── scripts/bench_api.py        # API latency benchmark (Phase 4/8)
│   ├── src/stocksense/
│   │   ├── __init__.py             # __version__
│   │   ├── settings.py             # pydantic-settings
│   │   ├── logging_config.py
│   │   ├── cli.py                  # Typer app: data (generate/load/validate/profile), db (apply-views/refresh/run-analysis), analytics (run/backfill), pipeline (all)
│   │   ├── db/
│   │   │   ├── engine.py           # create_engine, session factory
│   │   │   ├── models.py           # SQLAlchemy table definitions (migration source)
│   │   │   ├── sql_loader.py       # load_sql("api/overview_summary.sql") with caching
│   │   │   └── views.py            # apply_views(), refresh_materialized_views()
│   │   ├── generator/
│   │   │   ├── config.py           # preset dataclasses parsed from generator.toml
│   │   │   ├── rng.py              # seeded stream factory
│   │   │   ├── catalog.py          # regions, stores, categories, suppliers, products
│   │   │   ├── demand.py           # latent demand model
│   │   │   ├── promotions.py
│   │   │   ├── simulation.py       # day loop: receipts → sales → adjustments → ordering
│   │   │   └── writer.py           # CSV + manifest.json
│   │   ├── loader/copy_loader.py
│   │   ├── quality/checks.py       # runs sql/quality/*.sql, returns report
│   │   ├── analytics/
│   │   │   ├── config.py           # AnalyticsConfig parsed from analytics.toml
│   │   │   ├── distributions.py    # window demand distribution, quantile, sf, expected shortage
│   │   │   ├── forecasting.py      # censoring-aware EWMA + DOW + promo + fallbacks
│   │   │   ├── demand_patterns.py  # ADI/CV² classification
│   │   │   ├── leadtime.py         # lane estimates + PO ETA logic
│   │   │   ├── risk.py             # checkpoints, probability, shortage, tiers, projection
│   │   │   ├── policy.py           # safety stock, reorder point, order-up-to, order qty
│   │   │   ├── exposure.py         # financial exposure
│   │   │   ├── replenishment.py    # recommendation rules + priority ranking
│   │   │   ├── explanations.py     # drivers + deterministic text
│   │   │   ├── backtest.py         # rolling-origin evaluation
│   │   │   ├── scenario.py         # apply assumptions, recompute, aggregate
│   │   │   ├── types.py            # dataclasses / typed arrays for inputs & outputs
│   │   │   └── pipeline.py         # orchestrates a run (the only analytics module that touches DB)
│   │   ├── services/
│   │   │   ├── runs.py             # current run resolution
│   │   │   ├── overview.py
│   │   │   ├── risk_monitor.py
│   │   │   ├── positions.py
│   │   │   ├── suppliers.py
│   │   │   ├── forecasts.py
│   │   │   ├── scenarios.py
│   │   │   └── meta.py
│   │   └── api/
│   │       ├── app.py              # create_app(): CORS, middleware, routers, handlers
│   │       ├── deps.py             # DB connection dependency, current run dependency
│   │       ├── errors.py           # ApiError, handlers, error envelope
│   │       ├── pagination.py
│   │       ├── routers/            # health, meta, overview, risk, positions, suppliers, forecasts, scenarios
│   │       └── schemas/            # Pydantic models per router
│   └── tests/
│       ├── conftest.py
│       ├── unit/                   # no DB: analytics, generator determinism, explanations
│       ├── db/                     # needs Postgres: constraints, DQ, views, SQL analyses
│       ├── api/                    # FastAPI TestClient against test DB
│       └── fixtures/               # hand-computed golden cases (JSON)
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── next.config.ts
    ├── tsconfig.json
    ├── eslint.config.mjs
    ├── postcss.config.mjs
    ├── components.json              # shadcn config
    ├── vitest.config.ts
    ├── playwright.config.ts
    ├── Dockerfile
    ├── openapi.json                 # exported from backend (committed)
    ├── scripts/screenshots.ts       # Playwright screenshot capture (Phase 9)
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx           # AppShell, fonts, providers
    │   │   ├── page.tsx             # Overview
    │   │   ├── risk/page.tsx
    │   │   ├── positions/[storeId]/[productId]/page.tsx
    │   │   ├── suppliers/page.tsx
    │   │   ├── suppliers/[supplierId]/page.tsx
    │   │   ├── scenarios/page.tsx
    │   │   ├── methodology/page.tsx
    │   │   ├── not-found.tsx
    │   │   └── error.tsx
    │   ├── components/
    │   │   ├── ui/                  # shadcn primitives (generated)
    │   │   ├── layout/              # AppShell, Sidebar, TopBar, FilterBar, DatasetBadge
    │   │   ├── kpi/                 # KpiCard, KpiRow
    │   │   ├── charts/              # RiskTrendChart, RiskDistributionBar, CategoryHeatmap, StoreComparisonChart, InventoryProjectionChart, SalesHistoryChart, LeadTimeDistributionChart, ScenarioDeltaChart
    │   │   ├── tables/              # DataTable, RiskPositionsTable, SupplierTable, PurchaseOrderTable
    │   │   ├── risk/                # RiskTierBadge, ProbabilityMeter, ExplanationCard, RiskBreakdown, DriverChips, SensitivityPanel
    │   │   ├── scenario/            # AssumptionControl, ScopeSelector, ComparisonGrid, TierTransitionMatrix, TradeoffPanel
    │   │   └── states/              # LoadingSkeleton, EmptyState, ErrorState, AnalyticsNotReady
    │   ├── lib/
    │   │   ├── api/schema.ts        # generated by openapi-typescript (do not edit)
    │   │   ├── api/client.ts        # fetch wrapper, error parsing
    │   │   ├── api/hooks.ts         # useOverviewSummary(), useRiskPositions(), …
    │   │   ├── format.ts            # formatUsd, formatPct, formatUnits, formatDays, formatDate
    │   │   ├── url-state.ts         # typed search-param helpers
    │   │   ├── definitions.ts       # tooltip/definition text keyed by API field
    │   │   └── constants.ts         # tier labels/colors, metric polarity, enums mirrored from schema
    │   └── styles/globals.css       # Tailwind + design tokens (CSS variables)
    └── tests/
        ├── unit/
        ├── e2e/
        └── fixtures/                # shared formatter cases (copied from backend)
```

**Why `sql/` is at the repository root:** SQL is a first-class deliverable of the project. An interviewer opening the repository sees `sql/analyses/` immediately. The backend Docker build context is the repository root so the backend image includes `sql/`.

---

## 6. Module boundaries and dependency rules

```
api  ──▶ services ──▶ db (repositories via sql_loader)
              │
              └────▶ analytics (pure)  ◀── analytics/pipeline.py ──▶ db
generator ──▶ (writes CSV only)
loader ──▶ db
quality ──▶ db
```

Rules (enforced by code review and a simple import-lint test in `tests/unit/test_import_boundaries.py`):

1. `stocksense.analytics.*` (except `pipeline.py`) must not import `sqlalchemy`, `psycopg`, `fastapi`, or `stocksense.db`.
2. `stocksense.api.*` must not import `stocksense.analytics.*` directly; it calls services.
3. Nothing outside `stocksense.analytics.backtest` and `stocksense.analytics.pipeline` (evaluation step) may reference the `sim_truth` schema. A unit test greps `src/` and `sql/` (excluding `sql/pipeline/extract_latent_demand.sql` and `sql/quality/`) for `sim_truth` and fails on matches.
4. SQL strings longer than one line live in `.sql` files, not Python.
5. The frontend imports API types only from `src/lib/api/schema.ts`.

---

## 7. Data flows

### 7.1 Batch pipeline (CLI)

| Stage | Command | Input | Output | Failure behavior |
|-------|---------|-------|--------|------------------|
| 1 Generate | `stocksense data generate --preset standard --seed 42` | `generator.toml` | `data/generated/standard/*.csv`, `manifest.json` | Abort; no partial files (write to temp dir, then rename) |
| 2 Load | `stocksense data load --path data/generated/standard` | CSVs | `ops.*`, `sim_truth.*` populated (truncate-then-COPY in one transaction) | Rollback transaction |
| 3 Validate | `stocksense data validate` | `ops.*` | DQ report printed + exit code | Exit 1 if any `error` severity check returns rows |
| 4 Views | `stocksense db apply-views` / `stocksense db refresh` | `sql/views/*.sql` | Views created; materialized views refreshed | Abort |
| 5 Analytics | `stocksense analytics backfill --weeks 12` then `stocksense analytics run --evaluate` | `ops`, `analytics` views | `analytics.analytics_runs` + outputs | Run row marked `failed` with error message; previous successful run remains current |
| 6 Serve | `uvicorn stocksense.api.app:app` | `analytics.*` | JSON | 503 `ANALYTICS_NOT_READY` if no successful run |

`stocksense pipeline all --preset standard --seed 42` executes stages 1–5 in order.

### 7.2 Request flow (API)

1. Router validates query/body with Pydantic (422 on failure).
2. Dependency `get_current_run()` executes `SELECT run_id, as_of_date FROM analytics.v_current_run` (≤ 1 ms). Raises 503 if none.
3. Service calls repository function, which executes a named SQL file with bound parameters (`:run_id`, `:store_ids`, …) via SQLAlchemy Core `text()`.
4. Service maps rows → Pydantic response models (units and definitions documented in schema `Field(description=...)`).
5. Response returned with `X-StockSense-Run-Id` and `X-StockSense-As-Of` headers.

### 7.3 Scenario flow

1. `POST /api/v1/scenarios/evaluate` with scope and assumptions.
2. Scenario service obtains **baseline inputs** for the current run from the in-process cache (loaded once per `run_id` from `analytics.inventory_risk_snapshots`, `analytics.demand_forecast_daily`, `analytics.supplier_lane_estimates`, and open PO extraction SQL).
3. Filters positions by scope; applies assumptions; calls `analytics.risk.score_positions()` and `analytics.policy.compute_policy()` — **the same functions used by the pipeline**.
4. Aggregates baseline vs scenario; returns.

---

## 8. Configuration management

### 8.1 Environment variables (`.env`, template `.env.example`)

| Variable | Default (local) | Used by |
|----------|-----------------|---------|
| `POSTGRES_USER` | `stocksense` | compose |
| `POSTGRES_PASSWORD` | `stocksense` | compose |
| `POSTGRES_DB` | `stocksense` | compose |
| `POSTGRES_HOST_PORT` | `5433` | compose |
| `DATABASE_URL` | `postgresql+psycopg://stocksense:stocksense@localhost:5433/stocksense` | backend |
| `TEST_DATABASE_URL` | `postgresql+psycopg://stocksense:stocksense@localhost:5433/stocksense_test` | tests |
| `STOCKSENSE_ENV` | `local` | backend (`local`, `test`, `docker`) |
| `LOG_LEVEL` | `INFO` | backend |
| `API_CORS_ORIGINS` | `http://localhost:3000` | backend |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | frontend |
| `ANALYTICS_CONFIG_PATH` | `backend/config/analytics.toml` | backend |
| `GENERATOR_CONFIG_PATH` | `backend/config/generator.toml` | backend |

Inside Docker Compose, `DATABASE_URL` uses host `db` and port `5432`.

### 8.2 Model and generator parameters

- `backend/config/analytics.toml` — all parameters in 00 §4.2. Parsed with `tomllib` (standard library) into a frozen dataclass `AnalyticsConfig`. The full parsed config is serialized to JSON in `analytics.analytics_runs.config` for every run.
- `backend/config/generator.toml` — presets (`small`, `standard`, `large`) and named demo events. Parsed into `GeneratorConfig`.
- No other configuration files. No parameter is hardcoded in more than one place; tests import values from config.

---

## 9. Local execution model

### 9.1 Docker Compose services

```yaml
# docker-compose.yml (specification — Codex writes the actual file)
services:
  db:
    image: postgres:17
    environment: [POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB from .env]
    ports: ["${POSTGRES_HOST_PORT:-5433}:5432"]
    volumes: [pgdata:/var/lib/postgresql/data, ./docker/initdb:/docker-entrypoint-initdb.d:ro]  # initdb creates stocksense_test
    healthcheck: pg_isready -U stocksense, interval 5s, retries 20
    command: ["postgres", "-c", "shared_buffers=512MB", "-c", "work_mem=32MB", "-c", "maintenance_work_mem=256MB"]
  api:
    build: {context: ., dockerfile: backend/Dockerfile}
    env_file: .env
    environment: {DATABASE_URL: postgresql+psycopg://stocksense:stocksense@db:5432/stocksense, STOCKSENSE_ENV: docker}
    depends_on: {db: {condition: service_healthy}}
    ports: ["8000:8000"]
    profiles: ["full"]
  web:
    build: {context: ./frontend}
    environment: {NEXT_PUBLIC_API_BASE_URL: http://localhost:8000/api/v1}
    depends_on: [api]
    ports: ["3000:3000"]
    profiles: ["full"]
volumes: {pgdata: {}}
```

Two supported modes:

- **Development mode (default):** only `db` runs in Docker; API and web run natively with hot reload (`make api`, `make web`).
- **Full demo mode:** `docker compose --profile full up --build` runs all three services; the pipeline runs inside the `api` container via `make demo-docker`.

### 9.2 Makefile targets (binding names)

| Target | Action |
|--------|--------|
| `make setup` | `uv sync` in `backend/`; `npm ci` in `frontend/`; copy `.env.example` → `.env` if missing |
| `make db-up` | `docker compose up -d db` and wait for health |
| `make db-down` | `docker compose down` |
| `make db-reset` | Drop and recreate `stocksense` and `stocksense_test` databases, then `make migrate` |
| `make migrate` | `alembic upgrade head` then `stocksense db apply-views` |
| `make seed PRESET=standard SEED=42` | generate → load → validate → refresh views |
| `make analytics` | `stocksense analytics backfill --weeks 12` then `stocksense analytics run --evaluate` |
| `make pipeline` | `make migrate seed analytics` |
| `make api` | `uvicorn stocksense.api.app:app --reload --port 8000` |
| `make web` | `npm run dev` in `frontend/` |
| `make dev` | `make db-up pipeline` then prints instructions to run `make api` and `make web` in two terminals |
| `make demo-docker` | Full compose profile + pipeline inside the api container |
| `make test` | `make test-backend test-frontend` |
| `make test-backend` | `pytest` (unit + db + api), using `TEST_DATABASE_URL` |
| `make test-frontend` | `npm run test` (Vitest) |
| `make e2e` | Playwright against running API + web |
| `make lint` | `ruff check`, `ruff format --check`, `npm run lint` |
| `make typecheck` | `mypy src/stocksense/analytics`, `npm run typecheck` |
| `make openapi` | Export OpenAPI JSON from the app (no server) to `frontend/openapi.json`, then `npm run gen:api` |
| `make check-openapi` | Fails if regenerated `schema.ts` differs from committed version |
| `make explain` | Run `sql/explain/*.sql` and write output to `docs/perf/raw/` |
| `make schema-dump` | `pg_dump --schema-only` → `sql/schema/ddl_reference.sql` |
| `make verify` | `lint typecheck test check-openapi` (the "everything green" gate) |

### 9.3 Current Phase 0 checkpoint commands (2026-10-09)

The runnable setup currently stops at the health page: `make setup`, `make db-up`, then
`make api` and `make web` in separate terminals. Setup uses locked dependencies and
preserves the root `.env`. OpenAPI commands currently generate/check health-only types.
`make migrate`, `seed`, `db-reset`, `analytics`, `pipeline`, `dev`, `demo-docker`,
`explain`, and `schema-dump` explicitly fail until their phase implementation exists.
`make verify` includes real PostgreSQL tests and must not be reported passing without
Docker. See README and IMPLEMENTATION_STATUS.md for observed results. The target
interfaces in §9.2 remain binding as their phases are implemented.

### 9.4 Full-project fresh-clone procedure (future target)

```bash
brew install uv node@22          # once; Docker Desktop must be installed and running
git clone <repo> && cd StockSense
make setup
make db-up
make pipeline                    # migrate + generate standard dataset + load + validate + analytics
make api                         # terminal 1 → http://localhost:8000/docs
make web                         # terminal 2 → http://localhost:3000
```

---

## 10. Error handling

### 10.1 Backend

- All API errors return the envelope:

```json
{ "error": { "code": "POSITION_NOT_FOUND", "message": "No position for store_id=99, product_id=12 in run 14.", "details": {"store_id": 99, "product_id": 12} } }
```

- Error codes and HTTP statuses are listed in 08 §3.
- Unexpected exceptions → 500 `INTERNAL_ERROR` with a generic message; full traceback logged with request ID. Stack traces are never returned in responses.
- Pipeline errors: the run row is updated to `status='failed'`, `error_message` set to the exception summary; CLI exits non-zero; the previous successful run stays current.

### 10.2 Frontend

- `client.ts` parses the error envelope into an `ApiError` class (`status`, `code`, `message`).
- `ANALYTICS_NOT_READY` (503) renders the `AnalyticsNotReady` component with the exact command to run.
- Network failure renders `ErrorState` with a retry button (calls `refetch()`).
- Next.js `error.tsx` catches render errors per route.

---

## 11. Logging

- Python standard `logging`, configured once in `logging_config.py`.
- Format (local): `2026-10-09T15:20:01Z INFO stocksense.analytics.pipeline run_id=14 step=forecast positions=4800 elapsed_ms=2310`.
- Key-value style messages; JSON formatting is not required.
- API middleware assigns `X-Request-ID` (uuid4 if absent), logs method, path, status, duration.
- Pipeline logs one line per stage with row counts and elapsed time; these lines are also persisted in `analytics_runs.step_timings` (JSON) for performance reporting.
- Log levels: `INFO` default; `DEBUG` prints SQL file names and parameter keys (never full data).

---

## 12. Database migrations

- **Alembic** manages all tables, constraints, indexes, enums, and schemas. Migration source: `stocksense/db/models.py` (SQLAlchemy 2.0 declarative). Autogenerate is allowed **only as a starting point**; every migration is reviewed to include CHECK constraints, partial unique indexes, and BRIN indexes that autogenerate misses.
- Planned revisions:
  1. `0001_schemas_and_reference` — schemas `ops`, `analytics`, `sim_truth`; enums; reference tables.
  2. `0002_operational_facts` — sales, snapshots, POs, lines, receipts, adjustments, promotions.
  3. `0003_analytics_outputs` — runs, forecasts, evaluations, lane estimates, risk snapshots, recommendations.
  4. `0004_sim_truth` — latent demand.
- **Views are repeatable migrations** (ADR-011): `sql/views/NNN_name.sql` files, each beginning with `DROP VIEW/MATERIALIZED VIEW IF EXISTS … CASCADE;` followed by `CREATE …`. `stocksense db apply-views` executes them in filename order inside one transaction. `make migrate` always runs Alembic first, then views.
- Downgrades are implemented for every Alembic revision.

---

## 13. Caching

| What | Where | Key | Invalidation |
|------|-------|-----|--------------|
| Analytics results | PostgreSQL tables (precomputed by pipeline) | `run_id` | New successful run |
| `mv_daily_position` | Materialized view | — | `stocksense db refresh` after load |
| Current run lookup | Not cached (cheap query) | — | — |
| `/meta`, `/filters` responses | `functools.lru_cache` in service | `run_id` | Key change |
| Scenario baseline inputs | Module-level dict in `services/scenarios.py` | `run_id` | Key change; max 2 entries |
| Frontend | TanStack Query | query key incl. filters | `staleTime` 5 min; manual refetch on error |

No HTTP caching headers beyond defaults; no external cache.

---

## 14. Test organization (summary — full plan in 10)

| Suite | Location | Needs DB | Command |
|-------|----------|----------|---------|
| Analytics unit | `backend/tests/unit/` | No | `pytest -m unit` |
| Generator determinism | `backend/tests/unit/test_generator_*.py` | No | `pytest -m unit` |
| DB constraints & DQ | `backend/tests/db/` | Yes (small preset loaded once per session) | `pytest -m db` |
| SQL analyses | `backend/tests/db/test_sql_analyses.py` | Yes | `pytest -m db` |
| API | `backend/tests/api/` | Yes | `pytest -m api` |
| Frontend unit | `frontend/tests/unit/` | No | `npm run test` |
| E2E | `frontend/tests/e2e/` | Full stack | `npm run e2e` |

---

## 15. Architecture Decision Records

### ADR-001 — PostgreSQL rather than SQLite for the final application

- **Context:** The project must demonstrate serious SQL: window functions, CTEs, materialized views, statistical aggregates, indexes, and query plans; it must load ~1.7M fact rows (sales + snapshots).
- **Options:** SQLite; DuckDB; PostgreSQL.
- **Decision:** PostgreSQL 17.
- **Rationale:** Industry-standard OLTP/analytics database expected in analyst interviews; supports `percentile_cont`, `FILTER`, `DISTINCT ON`, `generate_series`, materialized views with concurrent refresh, BRIN indexes, schemas, `EXPLAIN (ANALYZE, BUFFERS)`, and CHECK/partial unique constraints. SQLite lacks materialized views and robust date/statistical functions; DuckDB is excellent for analytics but less representative of operational databases and weaker for constraint demonstrations.
- **Consequences:** Requires Docker locally. Tests require a running Postgres.
- **Risks:** Docker not installed on the student's Mac → README documents Docker Desktop installation; `make db-up` checks Docker availability with a clear message.

### ADR-002 — FastAPI for the backend API

- **Context:** Need a Python API (analytics are Python) with typed contracts.
- **Options:** Flask; Django REST Framework; FastAPI.
- **Decision:** FastAPI + Pydantic v2.
- **Rationale:** Automatic OpenAPI schema enables generated TypeScript types; Pydantic gives validation with descriptive errors; minimal boilerplate; same language as analytics so the Scenario Lab can call analytics functions directly.
- **Consequences:** Async not required; endpoints are sync `def` using a thread pool (SQLAlchemy sync engine) — simpler and adequate.
- **Risks:** Over-engineering async → explicitly use sync endpoints.

### ADR-003 — Next.js (App Router) for the frontend

- **Context:** The UI must look like a premium SaaS product, with routing, layouts, and strong TypeScript support.
- **Options:** Plain React + Vite; Next.js; Streamlit/Dash.
- **Decision:** Next.js with TypeScript, Tailwind, shadcn/ui, Recharts.
- **Rationale:** Streamlit/Dash look like internal prototypes and limit design control; Next.js layouts and file routing reduce boilerplate; shadcn/ui gives accessible, unbranded, professional primitives.
- **Consequences:** Pages are client components fetching from the API (no server-side data fetching), which keeps one data path and makes loading/error states explicit.
- **Risks:** Next.js version churn → pin exact versions; avoid experimental features (no Server Actions, no PPR).

### ADR-004 — SQL owns relational transformations and KPIs

- **Context:** The portfolio's central claim is SQL competence; also, joins/aggregations over ~1M rows are fastest in the database.
- **Options:** Load raw tables into pandas and compute everything in Python; compute features in SQL.
- **Decision:** SQL computes: daily position integration and availability status, PO line/PO status derivation, supplier/lane lead-time statistics, on-time/in-full metrics, category day-of-week profiles, ABC classes, stockout episodes (gaps and islands), reconciliation checks, all dashboard aggregations and rankings.
- **Rationale:** Visible, reviewable, reusable SQL; less data movement; same SQL serves analyses, pipeline, and API.
- **Consequences:** Pipeline SQL must be point-in-time (parameterized by `:as_of`) to avoid leakage.
- **Risks:** Logic split across languages → 04 §7 has an explicit SQL-vs-Python responsibility table.

### ADR-005 — Python owns forecasting, probability, and decision rules

- **Context:** Forecasting with censoring, distribution quantiles (Normal, Negative Binomial), expected-shortage integrals, rule-based recommendations, and scenario recomputation.
- **Options:** PL/pgSQL; Python.
- **Decision:** Python with NumPy/pandas/SciPy, as pure functions.
- **Rationale:** SciPy provides correct, tested distribution functions; pure functions are unit-testable with hand-computed fixtures; the scenario engine reuses them verbatim.
- **Consequences:** Pipeline moves ~270k rows (56-day window) into pandas per run; acceptable.

### ADR-006 — Explainable statistical forecasting first

- **Context:** The student must explain the model in an interview; the brief forbids unexplained complexity.
- **Options:** Moving average; exponential smoothing; Croston/TSB for intermittent; gradient boosting; Prophet.
- **Decision:** Censoring-aware EWMA level × category day-of-week index × planned promotion lift, with documented fallbacks (05 §3).
- **Rationale:** Every forecast can be reproduced by hand; handles censoring explicitly; performs reasonably on retail daily data; backtested against naive baselines.
- **Consequences:** No trend or annual seasonality modeling → documented limitation (October Lawn & Garden over-forecast).

### ADR-007 — Simulated data for the portfolio

- **Context:** Public datasets with joint store-SKU daily sales, inventory balances, POs, and supplier receipts essentially do not exist; corporate data is confidential.
- **Options:** Public sales-only datasets (e.g., M5) + invented inventory; fully synthetic causal simulation.
- **Decision:** Fully synthetic, deterministic, causal simulation with labeled provenance.
- **Rationale:** Internally consistent inventory flows (reconciliation holds), known ground truth enables a simulation-only evaluation, no licensing issues, reproducible with a seed.
- **Consequences:** Findings describe the simulation, not real retail; UI and docs say so.

### ADR-008 — Advanced ML excluded from the MVP

- **Context:** ML adds training infrastructure, feature leakage risk, and explanation burden.
- **Decision:** No ML in P0/P1. P2 may add ML only if it beats the baseline on the same leakage-free backtest and is presented side-by-side.
- **Rationale:** A well-evaluated simple model is more credible than an unevaluated complex one.

### ADR-009 — Modular monolith rather than microservices

- **Context:** One developer, one laptop, one demo.
- **Decision:** Single backend package for CLI and API; single frontend.
- **Rationale:** Shared analytics code between pipeline and Scenario Lab guarantees identical math; one deployment unit; trivial local setup.
- **Consequences:** Module boundaries enforced by import rules (§6) rather than network boundaries.

### ADR-010 — Batch analytics refresh with versioned runs

- **Context:** Forecasting + risk for 4,800 positions takes seconds; dashboards must be fast and consistent.
- **Options:** Compute on request; compute on startup; scheduled job; explicit command.
- **Decision:** Explicit command (`make analytics`) writing results keyed by `run_id`; API serves the latest successful `current` run. Weekly backfill runs supply trend history.
- **Rationale:** Simplest reliable approach; reproducible; failed runs don't corrupt the dashboard; lineage via `run_id` and stored config.
- **Consequences:** Data changes require re-running analytics (documented). No scheduler.

### ADR-011 — Views as repeatable SQL files, tables via Alembic

- **Context:** Views evolve with analytics; Alembic revisions embedding view SQL become unreadable and non-reproducible if they read files.
- **Decision:** Tables/constraints/indexes via Alembic; views via ordered, idempotent `sql/views/*.sql` files applied after migrations.
- **Rationale:** View SQL stays readable and reviewable as portfolio artifacts; idempotent re-application is safe.
- **Risks:** A view referencing a dropped column fails at apply time → `make migrate` runs both steps, and CI-style `make verify` runs DB tests that exercise every view.

### ADR-012 — Generated TypeScript types from OpenAPI

- **Context:** Backend and frontend schemas must not drift.
- **Decision:** Export OpenAPI JSON from FastAPI (`make openapi`), generate `schema.ts` with `openapi-typescript`, commit both; `make check-openapi` fails on drift.
- **Rationale:** One source of truth (Pydantic models).
