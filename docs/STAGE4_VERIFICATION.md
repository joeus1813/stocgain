# Stage 4 verification and final handoff — 2026-10-14

**Stage 3 gates pass. Stage 4 is not fully accepted: isolated fresh-clone setup/pipeline verification is outstanding.** The owner asked to wrap up; the implementation and evidence are preserved in a local checkpoint. No existing dataset/volume was deleted, and no remote publication or deployment was performed by this execution. Owner-created commit 846e292 and port-3050 settings were preserved.

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

## Outstanding acceptance and explicit deferrals

- **Fresh-clone setup and pipeline verification**: script prepared, not successfully executed. This blocks full Phase 9/Stage 4 acceptance. Do not remove the active database or volume to test it.
- **Full Compose application image/hosting**: unverified. No public deployment or remote write performed.
- Optional compact-table density toggle and additional chart-data disclosures deferred: existing dense tables and position data disclosure remain useful; these are P1 deferrals permitted by Phase 8.
- Cold first load ~7s; existing simulated-data calibration/model assumptions and five high development dependency advisories remain. MIT owner placeholder requires owner confirmation before public publication.
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
