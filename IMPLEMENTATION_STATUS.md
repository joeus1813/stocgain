# stocgain implementation status

Updated 2026-10-09 (America/New_York).

Official product: **stocgain.** — Predictive Retail Inventory Intelligence Platform. Tagline: *Predict stockouts. Replenish smarter.* The name combines “Stock Again” and “Stock + Gain”.

**Overall: Stage 1 incomplete; Phase 0 is complete and Phase 1 is beginning.** The former Docker blocker was resolved after local socket permission was approved. Stage 2 / original Phase 3 forecasting has not started.

## Completed foundation work

- Preserved supplied documents in initial Git commit `e1e45fe`; branch `stage-1-foundation`.
- Monorepo directories, `.gitignore`, `.env.example`, MIT license, README, Makefile.
- Locked Python 3.12/uv environment; FastAPI health endpoint with actual `SELECT 1`, unavailable state, CORS, request IDs, error envelopes, lifecycle-owned SQLAlchemy engine.
- Alembic environment configured, with **zero schema revisions**.
- PostgreSQL 17 Compose definition, test database init SQL, optional API/web Dockerfiles (not executed).
- Next.js temporary health client using TanStack Query; generated health OpenAPI types; Tailwind v4 tokens and shadcn configuration; no product pages.
- pytest unit/integration tests, Vitest/RTL health and root-env regression tests, Playwright full-stack health acceptance test.
- Compact IMPLEMENTATION_CONTRACT.md, phase log, decisions log and implementation plan.
- Independent code review; important root-environment bug reproduced by regression and fixed. No remaining important finding in reviewed Phase 0 scope; one deferred config-path issue below.

## Actual database results

Tables created: **0**. Views created: **0**. Generated datasets: **none** (0 rows). Migrations, deterministic generator, COPY loader, all 18 DQ checks, 15 analyses and EXPLAIN measurements are **not implemented or verified**. Specification inventory is 26 tables and 12 views, not an observed database inventory.

## Verification (2026-10-09)

Machine: macOS 15.6.1, arm64; Python 3.12.7; Node 22.23.3; uv 0.13.0. Project-local uv/Node were installed into ignored `.tools` because global prerequisites were absent. Commands below used those executables on PATH and `UV_CACHE_DIR=/private/tmp/stocksense-uv-cache`.

| Command | Observed result |
|---|---|
| `make setup` | PASS: locked uv sync and npm ci; existing .env preserved; npm advisories below |
| `make db-up` | FAIL: `make: docker: No such file or directory` |
| `make lint` | PASS: Ruff check + 23 files formatted; ESLint zero warnings/errors on final run |
| `make typecheck` | PASS: strict mypy, 20 source files; Next route types + tsc |
| `backend/.venv/bin/pytest backend/tests/unit -q` | PASS: 11 tests, 0.34 s final isolated run |
| `make test` | FAIL: 11 passed, 1 failed in 0.50 s; `test_health_against_real_postgres` reports unavailable. Make stops before frontend target |
| `make test-frontend` | PASS: 4 tests across 2 files, 0.899 s final standalone run |
| `make openapi` and `make check-openapi` | PASS: health-only JSON and TypeScript regeneration/drift check |
| `npm run format:check --prefix frontend` | PASS |
| `npm run build --prefix frontend` | PASS after root-env regression fix: compiled in 379 ms, TypeScript 1.267 s, 3 static pages generated in 252 ms |
| `make api` + `curl -sS http://localhost:8000/api/v1/health` | HTTP 200: status ok, database unavailable, analytics_ready false, current_run_id null |
| `make web` + `make e2e` (before Docker access) | Browser displayed the former product badge and `API: ok · Database: unavailable`; 1 test failed at required Database: ok assertion (5.3 s) |
| `make verify` | FAIL at real DB test: 11 passed, 1 failed in 0.59 s; lint/typecheck passed first |
| `git diff --check` | PASS before final checkpoint |

Test assertions were not skipped or weakened to conceal the missing database. Initial frontend test reached an unrelated ::1:3000 service; IPv4 browser resolution now selects this stack, leaving that service untouched. Initial sandboxed Next build could not bind its worker port; retry with approved local-process permissions passed. Own API/web processes were stopped after verification.

No SQL/performance claims are available. Build/test durations above are observed development checks, not business or database benchmarks.

## Known problems and next steps

1. **Install and start Docker Desktop**, then run `make db-up`, `make api`, `make web`, `make verify`, `make e2e`. Complete and record Phase 0 DoD before proceeding.
2. npm audit: five high development-tool advisory entries rooted in unpatched braces 3.0.3 through Next ESLint. Current selected lint peers require ESLint 9, which npm marks deprecated. No audit suppression or incompatible forced downgrade was used.
3. Deferred review minor: root .env gives relative analytics/generator config paths. They are unused now; normalize against REPOSITORY_ROOT before Phase 1 consumes them. Cost if deferred too long: config lookup fails when running from backend cwd.
4. Phase 1: all specified migrations/tables, deterministic small+standard simulator, transactional COPY, 18 DQ checks/corruption tests, schema dump and timings.
5. Phase 2: 12 views, as-of extraction, 15 analyses, point-in-time tests, EXPLAIN measurements, compatibility verification against forecasting specification.
6. Only after those checks can Stage 1 be marked complete and Stage 2 begin. No product decision is currently required; the blocker is the missing Docker prerequisite.
7. Owner may replace MIT `<Project Owner>` before publishing, per original spec.

For this workstation's already-installed local tools:

```bash
export PATH="$PWD/.tools/bin:$PWD/.tools/node/node_modules/node/bin:$PATH"
export UV_CACHE_DIR=/private/tmp/stocksense-uv-cache
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright"
```

Normal clones use globally installed uv/Node 22 and `npx playwright install chromium` as documented in README. `.tools` is intentionally not committed.

## Git checkpoint

Original design baseline: `e1e45fe`. Final foundation checkpoint is tagged `stage-1-incomplete-phase-0`; it explicitly records incompleteness. No remote/push/merge or destructive Git operation.

## 2026-10-09 continuation

Docker Server 29.8.2 and Compose 5.5.1 verified through the installed CLI path with approved local socket access; no reinstall. Existing `stocksense` PostgreSQL 17.11 container is healthy on localhost:5433. SQLAlchemy connected and returned the server version. Owner-directed rebrand updated visible name, tagline, product descriptions, Python distribution/module/CLI, npm package, metadata and design references. Existing `stocksense` PostgreSQL database/user/test database/Compose volume remain deliberately unchanged; no second database was introduced.

Phase 0 gate: `make test` passed 12 backend and 4 frontend tests; `make e2e` passed its one browser test (1.6 s); `make lint`, `make typecheck`, `make check-openapi` passed. Real HTTP health reported database ok. Earlier failure table above is historical from before Docker was available. Phase 1 is now permitted to start. Stage 1 remains incomplete until Phases 1–2 pass their own gates.

## Phase 1 checkpoint (2026-10-09)

Alembic revisions `0001`–`0004` now create the 26 specified physical tables in the existing PostgreSQL 17 database. The empty test database completed upgrade, downgrade-to-base, and re-upgrade. The main database readback reported revision `0004` and 26 application tables. Three PostgreSQL schema/constraint tests passed, and `make schema-dump` wrote the inspected DDL reference. The generator presets and independent RNG stream helper are present. No operational rows or standard dataset have been loaded. SQLAlchemy model metadata, generator, loader, quality checks, SQL views/analyses, and Phase 1/2 acceptance tests remain to implement. Stage 1 is **not complete** and is **not ready for Stage 2**.

Latest verification: `make lint typecheck test check-openapi` exited 0 after the migrations and partial generator work. It ran 16 backend tests (including three against live PostgreSQL) and four frontend tests; Ruff, mypy, ESLint, TypeScript and the OpenAPI drift check passed. This does not satisfy the Phase 1 or Phase 2 acceptance criteria.
