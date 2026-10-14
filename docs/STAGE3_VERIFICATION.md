# Stage 3 verification — 2026-10-13

Continued verified Stage 2 `646e2e2` on the existing branch, single agent. Phases 5–6 and Phase 7 functional work are implemented. **Stage 3 is not fully accepted: docs/07 §10.4 AC5 (Scenario Lab p95 <1.5 seconds) remains unmet.** No Stage 4 work, deployment, remote Git change, data replacement, migration change or model formula change.

## Delivered and checked

| Area | Implementation and evidence |
|---|---|
| Foundation | Typed API client, run-keyed TanStack Query caches, URL/global filters, navigation, provenance badge on all pages, canonical tokens and shared formatters, loading/error/empty states, mobile shell; shared 20-case Python/TypeScript formatter fixtures |
| Executive Overview | Six live KPIs, priorities, risk distribution/trends, SKU/store/category views and drilldowns, stored forecast evaluation, service health |
| Risk Monitor | Server filtering/sorting/pagination, debounced search, advanced filters, scope summary, CSV export, position navigation with preserved return state |
| Position detail | Actual explanations, coverage and estimated risk, inventory/forecast charts, censored sales, policy/financial/checkpoint breakdowns, POs, recommendation and copy summary, sensitivity |
| Suppliers | Real summary/scatter/table, supplier detail, first-receipt on-time history, lead-time distribution, lanes and exposed positions |
| Scenario Lab | Four validated controls, scope, 400 ms debounce, request cancellation, retained results during updates, neutral comparison, tradeoffs, transitions, category and position changes, presets/reset, error handling |
| Methodology | Simulated-data provenance, live configuration/counts, documented assumptions/limitations/formulas, actual stored backtest results; explicitly requested in Stage 3 |

Six supporting P1 endpoints bring the API to all **22 specified paths**: CSV export, sensitivity, supplier summary/list/detail and forecast evaluation. Supplier integration checks compare against the existing PostgreSQL view and verify that future receipts do not change historical metrics. All UI business values come from real APIs; failure responses are stubbed only in browser tests. Existing engines are reused for scenarios and sensitivity. Older stored explanation probability text is normalized at presentation only; persisted strings and calculations are unchanged.

## Commands actually run

Environment: local macOS arm64, PostgreSQL 17.11 via existing Docker Desktop volume, Python 3.12.7, Node 22.23.3; browser tests use Playwright Chromium and the Next.js production build. Exact benchmark OS/runtime metadata is in the JSON evidence.

| Command | Actual result |
|---|---|
| `make lint typecheck test check-openapi` | Lint/type checks passed; backend **259 passed, 1 failed, 2 deselected**, 47.20 s. Failure was missing descriptions/units in new API schema metadata. Later steps did not execute in this command. |
| `backend/.venv/bin/pytest backend/tests/api/test_phase6.py backend/tests/api/test_contracts.py backend/tests/api/test_positions.py -q` after fix | **16 passed**, 11.57 s; includes schema metadata/CSV contract and historical supplier receipt regression. |
| `backend/.venv/bin/pytest backend/tests/unit/test_formatting.py -q` | **20 passed**, 0.02 s. |
| `make lint typecheck test-frontend check-openapi` after final UI fix | Passed: Ruff/102-file formatting, ESLint, mypy/67 sources, strict TypeScript; **38 frontend tests passed**, 1.08 s; OpenAPI/generated types no drift. |
| `npm --prefix frontend run build` after final UI fix | Passed; compile 2.1 s, TypeScript 3.0 s; all application routes built. |
| `npm --prefix frontend run e2e -- --workers=1` against production | **11 passed**, 35.3 s. Includes real PostgreSQL health, exact KPI/API equality, filters/sort/page/drilldown, supplier/CSV, scenario behavior, 503/error/retry/404 and responsive routes. |
| `npm --prefix frontend run e2e -- risk.spec.ts responsive.spec.ts --workers=1` after last action-label fix | **3 passed**, 20.9 s; screenshots refreshed. |
| `npm --prefix frontend run format:check` | Passed; all matched files use Prettier style. |
| `node frontend/scripts/benchmark-scenario.mjs` | 20 successful real full-scope browser evaluations; performance result below. |

The complete backend suite was **not** rerun after the metadata repair: the failed contract test and affected API groups were rerun successfully, in accordance with targeted development verification. The two slow standard-data tests remain deselected by the existing default marker; Stage 1/2 data generation and verification were not repeated. Original comprehensive output and subsequent repair evidence are both retained under `docs/perf/raw/stage3_*`. Do not describe the initial comprehensive command as passing.

Other defects caught and fixed included search focus/state reset, cross-realm abort handling, CSV filename CORS exposure, mobile formula overflow, and an expedite action displaying an unrelated reorder quantity. Last fix has a unit regression plus the final browser regression above. Recharts entry animations are disabled to avoid misleading transitional chart screenshots.

## Actual PostgreSQL-backed readback

Final local API: healthy, database ok, analytics ready, current run **14**, as-of **2026-09-30**. Active positions **4,800** / distinct SKUs **400**; at risk **1,058**, critical **727**; estimated gross margin at risk **$122,138.83**, estimated revenue at risk **$327,737.92**; median cover **14.8 days**; supplier on-time rate **96.17%** over **7,161** due POs; end-of-day in-stock rate **92.13%**. Supplier summary: **48** suppliers, **8.9 days** mean lead time, **6** overdue open POs. These are simulated-data model/operational results, not realized business outcomes. Raw responses: [stage3_readback.json](perf/raw/stage3_readback.json).

## Scenario performance and acceptance gap

One production-browser benchmark of 20 distinct demand changes over the full **4,800** positions, with warm baseline/model cache. Measured from input through 400 ms debounce, HTTP response and settled rendered result; nearest-rank p95. Median **2241.609 ms**, p95 **2425.842 ms**, versus the **1,500 ms** target. All responses succeeded; latency criterion **fails**. [All samples and machine metadata](perf/raw/stage3_scenario.json); [reproducible script](../frontend/scripts/benchmark-scenario.mjs).

The earlier production disruption flow took 3,379 ms (server calculation 1,573.431 ms), a single observation rather than p95. Stage 2 previously measured warm HTTP p95 1,793.594 ms and cold replay 6,431.645 ms. These timings measure different paths and must not be substituted for one another. UI now provides loading feedback, retains previous results and cancels stale requests. Further backend optimization is deliberately deferred under the owner's instruction to avoid major Stage 2 optimization during frontend work; formulas and the 400 ms debounce are preserved. No timing threshold was loosened and AC5 remains open.

## Visual and failure-state evidence

Real production browser checked all six pages at **1440, 1280 and 390 px**, with no page-level horizontal overflow or uncaught page errors. Tables/heatmaps may scroll inside their containers. Screenshots at 1440/390 are in [screenshots/wip](screenshots/wip); Overview desktop and Position mobile were visually inspected after final fixes. Foundation 1280 screenshots are also retained. This does not claim an exhaustive accessibility audit or every possible empty/error state: the full Phase 8 responsive/axe audit remains out of scope. 503 and isolated widget 500/retry cases use test-only route stubs; successful recovery uses the actual API.

## Known limitations / resume

- **Phase 7 / Stage 3 acceptance remains open solely on the measured Scenario Lab latency criterion among the implemented phase checks.** Functional scenario neutrality, disruption direction, service-level tradeoff, reset and invalid inputs passed.
- Inherited simulation calibration advisory, model independence/censoring assumptions and development dependency advisories remain. No accuracy or business-impact claim is inferred from the UI.
- Stage 4 / Phases 8–9, public deployment, full Docker application profile and remote pushes were not performed or authorized. Methodology was included because the owner explicitly requested it in Stage 3.
- No user permission/manual step is pending. Follow-up should preserve this checkpoint and target scenario latency only if authorized; do not regenerate the existing dataset or rerun completed stages.

## Local launch (existing populated database)

Run in each terminal from the repository root:

```bash
cd /Users/yuminsong/Desktop/StockSense
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PWD/.tools/bin:$PWD/.tools/node/node_modules/node/bin:$PATH"
export UV_CACHE_DIR=/private/tmp/stocksense-uv-cache
```

With Docker Desktop running, terminal 1: `make db-up` then `make api`.
Terminal 2: `make web`. Open http://localhost:3050; API docs http://localhost:8000/docs.
No seed, migration or analytics rerun is needed for this existing verified dataset. For the production frontend used in tests, run `npm --prefix frontend run build` then `npm --prefix frontend run start` instead of `make web`. Use only one frontend process on port 3050.
