# stocgain.

**Predictive Retail Inventory Intelligence Platform**

*Predict stockouts. Replenish smarter.*

The name combines “Stock Again” and “Stock + Gain”.

Inventory intelligence for a fictional home-improvement retailer. **Simulated Retail Dataset**: no real retailer data or affiliation.

**Stage 1 is incomplete.** Phase 0 is verified, and the 26-table PostgreSQL schema is migrated. The temporary service-health page is the only UI. The data generator, loader, quality checks, SQL analyses, forecasting, business API, and dashboard remain unfinished. See [implementation status](IMPLEMENTATION_STATUS.md) and [phase progress](docs/PROGRESS.md).

## Prerequisites

- Python 3.12 and uv (lockfile created with uv 0.13.0)
- Node 22 (`nvm use`; `.nvmrc` selects the supported major) and npm
- Docker Desktop with Compose v2, installed and running

## Local setup

Run from the repository root:

```bash
make setup                       # root .env, locked Python + npm dependencies
make db-up                       # PostgreSQL 17, localhost:5433, test database too
make api                         # terminal 1: http://localhost:8000/api/v1/health
make web                         # terminal 2: http://localhost:3000
```

The temporary page calls the real API using TanStack Query. With PostgreSQL available it displays `API: ok · Database: ok`; otherwise it reports the actual unavailable state. Health always returns HTTP 200 for a live process; inspect its `database` field. Analytics readiness stays false until later phases implement run detection.

`.env.example` contains local-only example credentials. `make setup` preserves an existing `.env`; the backend and Next config load it from the repository root. Adjust both connection URLs if changing the database port or credentials. Never commit `.env`. `DATABASE_URL_PSQL` is the libpq form for future SQL tools. Only localhost ports are published by Compose.

Optional container configuration: `docker compose --profile full up --build`. The full profile has not been verified. Browser API URL is baked into the frontend image via the build argument; rebuild the image after changing it.

## Verification

```bash
make lint
make typecheck
make test                        # includes real PostgreSQL test; fails if DB unavailable
make openapi                     # health-only schema and generated TypeScript
make check-openapi
make verify                      # lint + types + tests + schema drift
cd frontend && npx playwright install chromium
cd .. && make e2e                # requires running API + web + PostgreSQL
```

DB-independent checks during setup troubleshooting:

```bash
uv run --project backend --locked pytest backend/tests/unit -q
make test-frontend
cd frontend && npm run build
```

Do not substitute these unit checks for the phase's PostgreSQL acceptance gate.

## Structure and next work

- `backend/src/stocgain/`: settings, logging, FastAPI health/errors, SQLAlchemy engine, CLI namespaces.
- `backend/migrations/`: four reversible Alembic revisions for the 26 specified physical tables.
- `frontend/`: Next App Router health client, Tailwind v4 tokens, shadcn configuration, generated API types, Vitest/Playwright tests.
- `sql/`: reserved directories for Phase 1 quality checks and Phase 2 SQL.
- `docs/00`–`docs/11`: authoritative product and engineering specifications.
- `IMPLEMENTATION_CONTRACT.md`: compact compatibility contract and planned data interfaces.

`make migrate`, `seed`, `db-reset`, `analytics`, `pipeline`, `dev`, `demo-docker`, and `explain` fail explicitly until their required implementations exist. `make schema-dump` writes the current database DDL to `sql/schema/current.sql`. No populated dashboard setup is claimed. Phase 1 follows the verified Phase 0 gate; Phase 2 follows Phase 1. Stop before original Phase 3 in this stage.

## Known limitations

Docker Desktop and PostgreSQL 17.11 are working locally. Phase 0's real database test and full-stack browser test passed. Four schema revisions passed an empty-test-database downgrade/re-upgrade round trip, and were applied to the existing project database. The schema is empty of retail facts; Compose image builds, data loading, reconciliation, analytical SQL, and query timings remain unverified.

npm reports five high-severity development-only advisory entries rooted in `braces` through the Next ESLint plugin; latest available braces 3.0.3 is affected. ESLint 9 is deprecated upstream but currently required by the selected React/import lint plugins. No forced incompatible downgrade or hidden warning suppression was applied. Track these in `docs/DECISIONS_LOG.md`.

The MIT copyright holder remains `<Project Owner>` as required by the Phase 0 specification; replace with the owner's preferred legal name before publishing.

Setup references used: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [shadcn manual installation](https://ui.shadcn.com/docs/installation/manual), [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/).
