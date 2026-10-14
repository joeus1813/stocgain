# Stage 4 verification and final handoff — 2026-10-14

**Stage 3 and Stage 4 required local acceptance gates pass.** The owner asked to wrap up; the implementation and evidence are preserved in a local checkpoint. No existing dataset/volume was deleted, and no remote publication or deployment was performed by this execution. Owner-created commit 846e292 and port-3050 settings were preserved.

## Final isolated acceptance — 2026-10-14

**Stage 4 is accepted for the local portfolio scope.** The remaining fresh-install and full-stack gates passed; public hosting/publication was not performed or approved.

- Ran `scripts/verify_fresh_setup.sh` from checkpoint `cba3f96`: clean locked install, migrations, standard dataset, DQ, all 13 analytics runs, full verification and production build succeeded (exit 0). Setup + pipeline **243 s**, pipeline **222 s**; generation **8.471 s**, load/validation **36.507 s**, separate DQ **9.112 s**. Fresh data contains **864,000 rows each** of sales, inventory and latent demand for 12 stores × 400 SKUs × 180 days. All **18 DQ checks returned zero violations**.
- `PYTEST_ADDOPTS="-m '' --cov=stocgain.analytics --cov-report=term-missing" make verify`: **270 backend tests passed in 96.38 s**, no slow-test deselection, **92% analytics coverage**; **38 frontend tests passed in 1.29 s**. Ruff/check-format, ESLint, mypy (67 source files), TypeScript and OpenAPI drift checks passed. Next.js production build passed.
- Built both application images with `docker compose --profile full build`, then `up -d --wait`: PostgreSQL, API and web healthy. Real API health reports database `ok`, analytics ready and current run **13**.
- All **14 Playwright tests passed in 1.2 min** against the isolated Docker stack: real KPI equality, filtering/sorting/pagination/drilldown, supplier CSV, scenario neutral/disruption/policy/reset, responsive layouts, failure/retry/empty states and accessibility. Six screens plus supplier detail had zero serious/critical axe violations at desktop/mobile sizes.
- Isolation: checkout `/private/tmp/stocgain-fresh-ZXmDDs/repo`, Compose project `stocgain_verify_1791997566`, PostgreSQL **55433**, API **18000**, web **13050**. The original database, volumes and port-3050 configuration were preserved. Containers/volume are retained for inspection. The clone began at `cba3f96`; only Compose host-port parameters and browser test URL parameters were copied in before final verification to exercise this isolated stack. Defaults remain 8000/3050; no business logic changed.
- Audited all **13 reachable commits / 568 unique blobs / 22,590,379 bytes** at `cba3f96`, including historical/deleted versions: no credential-pattern or sensitive-file findings. Runtime `.env`, dependencies, data, backups and tools are ignored; public local-development example credentials are intentional. Pattern scanning cannot prove arbitrary unknown secrets absent. Evidence: `perf/raw/stage4_secrets_audit.json`.
- MIT attribution is **Yumin Song**, explicitly supplied by the owner.
- Final readback: Docker Desktop stopped after the successful suites (socket absent). Restarted Desktop and the same isolated containers without changing volumes; all three became healthy again. API health returned `database=ok`, `analytics_ready=true`, `current_run_id=13`. Direct PostgreSQL counts confirmed sales/inventory/latent **864,000 each**. An initial ad-hoc readback used the wrong latent table name; corrected to `sim_truth.latent_demand`, with no schema or data changes.

Logs: `perf/raw/stage4_fresh_acceptance.txt`, `stage4_docker_build.txt`, `stage4_isolated_stack.txt`, and `stage4_isolated_browser.txt`. Earlier failed attempts below remain historical evidence, superseded by this successful full run.

The existing warm p95 **1.383 s** remains the dedicated 20-request benchmark, not a new result from this acceptance run. The isolated browser scenario changed real outputs (server **924.57 ms**, single UI update **2,750 ms** while the full regression suite was also running). This is neither a representative p95 nor a cold-start benchmark. Cold first load ~7 s, modest forecast improvement, five previously reported development dependency advisories, and optional P1 presentation deferrals remain documented limitations. Local acceptance is not public-production readiness.

## What changed

- Scenario profiling identified scalar SciPy inverse-CDF/PMF overhead (18,294 PPF calls in the profiled warm request). Equivalent count-tail and truncated-first-moment calculations remove redundant work; singular near-Poisson NB cases retain the reference finite sum. Model assumptions, family selection, safety-stock rounding, receipt timing and 400 ms UI debounce remain unchanged.
- Body/title/card text is 15/28/18 px with minimum 12px labels. KPI markup, muted-text and heatmap contrast were repaired. Scrollable tables/formulas are keyboard focusable; the icon-only mobile provenance badge has an accessible name.
- README, architecture references, real screenshots, third-party notices, honest forecast findings, two-minute demo, resume drafts and publication instructions are prepared.

## Actual performance

| Measurement | Result | Evidence |
|---|---:|---|
| Warm browser full-scope p50 | 1,330.588 ms | stage4_scenario.json |
| Warm browser full-scope p95 | **1,382.796 ms**, target <1,500 ms passes | 20 distinct demand changes; 4,800 positions; includes input/debounce/HTTP/render |
| First cold Scenario Lab load | **7,014.114 ms** | Fresh API process; page load plus baseline replay; not a warm p95 |
| Final neutral model calculation | 909.502 ms | stage4_models.json; single measurement |
| Rolling history: materialized view | 274.342 ms | q2_daily_history.txt, EXPLAIN ANALYZE |
| Equivalent history: base tables | 691.935 ms | q2_direct_ops.txt |
| Overview summary SQL | 242.576 ms | q5_overview_summary.txt |

SQL timings are retained measurements from the implementation session, not a new final-run benchmark. Machine: macOS arm64, Python 3.12.7, Node 22.23.3, PostgreSQL 17.11, Next production build and Playwright Chromium. Timing is machine/load dependent. No result-response cache was substituted for real changed-input calculations. Cold replay remains slower than the desired warmup target; previous results/loading states remain visible during calculation.

## Actual verification

1. The first final suite encountered Docker Desktop stopped and its daemon socket absent; it was interrupted. Docker Desktop and the existing PostgreSQL service were started before the healthy-DB run.
2. `PYTEST_ADDOPTS="-m '' --cov=stocgain.analytics --cov-report=term-missing" make verify`: lint/types passed; backend **268 passed, 2 failed in 88.04 s**, no default slow deselection, **92% analytics coverage**. Both failures expected localhost:3000 after the authorized 3050 change. Updated test expectations; `pytest backend/tests/unit/test_smoke.py -q`: **11 passed in 1.00 s**. The entire backend suite was not repeated after this test-only fix.
3. `make lint typecheck test-frontend check-openapi`: passed after final UI corrections; **38 frontend tests in 1.20 s**, strict types and generated schema clean. `npm --prefix frontend run build`: passed.
4. Full production `npm --prefix frontend run e2e -- --workers=1`: **12 passed, 2 failed in 1.2 min**. Passed real KPI equality, navigation, risk filtering/sort/page/drilldown, scenario neutral/disruption/policy/reset/invalid controls, suppliers/CSV and five-width responsive checks. Failures: axe keyboard-scroll/mobile-summary accessibility and the test's incorrect empty-search heading expectation.
5. After repairs, `npm --prefix frontend run e2e -- a11y.spec.ts states.spec.ts --workers=1`: **5 passed in 33.0 s**. Axe found **zero serious/critical violations** on the six primary pages plus supplier detail at 1440 and 390px. All six screens' 503/retry states and empty risk-search recovery passed. No rules were excluded or disabled.
6. `stocgain data validate`: **18 checks, all zero violations**, 9.022 s.
7. `python backend/scripts/verify_models.py`: succeeded against the original standard database. **All 4,800 neutral snapshots** match stored outputs within 1e-6 at storage precision; neutral aggregate deltas zero. 13 successful runs; current run14 has 4,800 forecasts/risks/recommendations, 201,600 daily forecasts, 7,206 checkpoints and 72 evaluation rows. Pipeline seconds in that output refer to stored historical runtimes, not a fresh pipeline execution.

Logs are in `docs/perf/raw/stage4_*`. Initial failures are retained, not relabeled as passing. Repairs were followed by relevant targeted tests; no second comprehensive suite was claimed. Screenshots in `docs/screenshots/` are real app captures, including 1440/390; responsive test covers 1440/1280/1024/768/390. Final focus/aria repairs do not alter screenshot appearance. Overview desktop was visually inspected.

## Forecast evidence

Observed in-stock WAPE: stocgain **57.66%**, naive28 **58.39%**, seasonal7 **77.96%**. The improvement is **0.73 percentage points / about 1.25% relative**, with positive model bias of 5.12%. On erratic demand, stocgain is worse (71.20% vs 69.01%). Hidden-demand evaluation is simulation-only (55.86% vs 57.40% naive); hidden truth never enters operational forecasting. See FORECAST_FINDINGS.md for segment data and limitations. No real-world accuracy, financial savings or stockout-reduction claim is supported.

## Earlier outstanding items (resolved above) and explicit deferrals

- **Fresh-clone setup and pipeline verification**: script prepared, not successfully executed. This blocks full Phase 9/Stage 4 acceptance. Do not remove the active database or volume to test it.
- **Full Compose application image/hosting**: unverified. No public deployment or remote write performed.
- Optional compact-table density toggle and additional chart-data disclosures deferred: existing dense tables and position data disclosure remain useful; these are P1 deferrals permitted by Phase 8.
- Cold first load ~7s; existing simulated-data calibration/model assumptions and five high development dependency advisories remain. MIT owner attribution was subsequently confirmed as Yumin Song.
- Public release readiness is conditional, not a claim of deployed/production readiness. See PUBLICATION_AND_DEPLOYMENT.md.

## Run locally

```bash
cd /Users/yuminsong/Desktop/StockSense
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PWD/.tools/bin:$PWD/.tools/node/node_modules/node/bin:$PATH"
export UV_CACHE_DIR=/private/tmp/stocksense-uv-cache
make db-up
make api
```

In another terminal, use the same directory/PATH and run `make web`; open http://localhost:3050. The current production frontend can instead run via `npm --prefix frontend run start` after a build. Do not start a second process on 3050 while the existing one is active. Existing populated data requires no seed/pipeline rerun.
