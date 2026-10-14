# stocgain implementation status

Updated 2026-10-14 (America/New_York).

**Stages 1–4 are accepted for the local portfolio scope. Final isolated fresh-install, full Docker stack and comprehensive regression verification passed on 2026-10-14. No public deployment or remote publication was performed.**

The current session preserves owner-created checkpoint `846e292`, the earlier `61eb8d7` port-3050 configuration, all project history, PostgreSQL data and model formulas. No remote changes, public deployment, purchases or data deletion were performed by this execution.

## Completed

- All six analytical screens, supplier detail and 22 API endpoints remain implemented with real PostgreSQL/model results.
- Scenario performance: replaced repeated scalar inverse-CDF work with equivalent count-tail/first-moment computations; preserved the original finite sum at numerically singular NB/Poisson boundaries. Golden/reference/scenario group: 43 passed in the implementation session.
- Actual warm browser benchmark: **p95 1,382.796 ms**, median 1,330.588 ms, 20 distinct 4,800-position updates including unchanged 400 ms debounce. Cold first page/model load: **7,014.114 ms**. Warm target passes; cold loading remains a documented limitation. Raw: `docs/perf/raw/stage4_scenario.json`.
- Readability: body 15px, title 28px, card headings 18px, minimum labels 12px, stronger muted-text/heatmap contrast. Corrected KPI description-list markup and added keyboard access to scrolling tables/formulas and a mobile dataset-badge accessible name.
- Desktop/mobile screenshots; five-width responsive check (1440/1280/1024/768/390), error/retry checks, forecast findings, README architecture, third-party notices, two-minute demo, resume drafts and publication/deployment preparation.

## Earlier verification (superseded by final isolated acceptance)

- First suite attempt encountered a stopped Docker daemon and was interrupted. Docker Desktop and the existing PostgreSQL service were started; no data was replaced.
- Healthy-DB comprehensive backend run: **268 passed, 2 failed**, 88.04 s; all 270 tests selected including slow standard-data tests; analytics coverage **92%**. Both failures expected port 3000 after the authorized change to 3050. Corrected the stale test origins; affected smoke group **11 passed** (1.00 s). Full backend suite was not repeated after that test-only fix.
- Final `make lint typecheck test-frontend check-openapi`: passed, **38 frontend tests**, 1.20 s; Ruff, mypy, ESLint, TypeScript and generated API drift checks clean. Production build passed.
- Full browser run: **12 passed, 2 failed** (1.2 min); failures identified missing keyboard scroll focus/mobile provenance name and an incorrect expected empty-search heading. After fixes, affected browser tests **5 passed in 33.0 s**; axe reports zero serious/critical violations on six primary screens plus supplier detail at desktop/mobile widths.
- Data validation: **all 18 DQ checks zero**, 9.022 s.
- `backend/scripts/verify_models.py`: succeeded; all **4,800** neutral position snapshots match stored values at canonical serialization precision, all aggregate neutral deltas zero. Current run 14 has 201,600 daily forecasts, 7,206 checkpoints and 72 evaluation rows. Measured neutral calculation 0.910 s; recorded pipeline duration is historical, not a new pipeline run.

## Remaining limitations and readiness

- Isolated fresh-clone setup, pipeline, verification and build passed; see the final acceptance record below.
- Cold Scenario Lab replay still takes about seven seconds; UI exposes loading and keeps previous results while updating.
- Optional compact-table density toggle and extra chart-data tables are deferred to avoid nonessential scope expansion; current tables and position observed-data disclosure remain functional.
- Full Compose application images and local stack passed. Public hosting remains unverified and requires owner approval. MIT attribution is Yumin Song. Five previously reported high development dependency advisories remain unresolved; no forced incompatible update was applied.
- Forecast improvement is modest: observed WAPE 57.66% versus naive 58.39% (0.73 percentage points); erratic-demand performance is worse. No business-benefit or real-retailer accuracy claim.

See [Stage 4 report](docs/STAGE4_VERIFICATION.md), [forecast findings](docs/FORECAST_FINDINGS.md), [demo/resume drafts](docs/INTERVIEW_DEMO.md), [publication instructions](docs/PUBLICATION_AND_DEPLOYMENT.md). Local launch: `make db-up`, `make api`, `make web`; frontend http://localhost:3050. Remote publication still requires explicit owner approval.

## Final isolated acceptance — 2026-10-14

**Stage 4 is accepted for the local portfolio scope.** The remaining fresh-install and full-stack gates passed; public hosting/publication was not performed or approved.

- Ran `scripts/verify_fresh_setup.sh` from checkpoint `cba3f96`: clean locked install, migrations, standard dataset, DQ, all 13 analytics runs, full verification and production build succeeded (exit 0). Setup + pipeline **243 s**, pipeline **222 s**; generation **8.471 s**, load/validation **36.507 s**, separate DQ **9.112 s**. Fresh data contains **864,000 rows each** of sales, inventory and latent demand for 12 stores × 400 SKUs × 180 days. All **18 DQ checks returned zero violations**.
- `PYTEST_ADDOPTS="-m '' --cov=stocgain.analytics --cov-report=term-missing" make verify`: **270 backend tests passed in 96.38 s**, no slow-test deselection, **92% analytics coverage**; **38 frontend tests passed in 1.29 s**. Ruff/check-format, ESLint, mypy (67 source files), TypeScript and OpenAPI drift checks passed. Next.js production build passed.
- Built both application images with `docker compose --profile full build`, then `up -d --wait`: PostgreSQL, API and web healthy. Real API health reports database `ok`, analytics ready and current run **13**.
- All **14 Playwright tests passed in 1.2 min** against the isolated Docker stack: real KPI equality, filtering/sorting/pagination/drilldown, supplier CSV, scenario neutral/disruption/policy/reset, responsive layouts, failure/retry/empty states and accessibility. Six screens plus supplier detail had zero serious/critical axe violations at desktop/mobile sizes.
- Isolation: checkout `/private/tmp/stocgain-fresh-ZXmDDs/repo`, Compose project `stocgain_verify_1791997566`, PostgreSQL **55433**, API **18000**, web **13050**. The original database, volumes and port-3050 configuration were preserved. Containers/volume are retained for inspection. The clone began at `cba3f96`; only Compose host-port parameters and browser test URL parameters were copied in before final verification to exercise this isolated stack. Defaults remain 8000/3050; no business logic changed.
- Audited all **13 reachable commits / 568 unique blobs / 22,590,379 bytes** at `cba3f96`, including historical/deleted versions: no credential-pattern or sensitive-file findings. Runtime `.env`, dependencies, data, backups and tools are ignored; public local-development example credentials are intentional. Pattern scanning cannot prove arbitrary unknown secrets absent. Evidence: `perf/raw/stage4_secrets_audit.json`.
- MIT attribution is **Yumin Song**, explicitly supplied by the owner.

Logs: `perf/raw/stage4_fresh_acceptance.txt`, `stage4_docker_build.txt`, `stage4_isolated_stack.txt`, and `stage4_isolated_browser.txt`. Earlier failed attempts below remain historical evidence, superseded by this successful full run.

The existing warm p95 **1.383 s** remains the dedicated 20-request benchmark, not a new result from this acceptance run. The isolated browser scenario changed real outputs (server **924.57 ms**, single UI update **2,750 ms** while the full regression suite was also running). This is neither a representative p95 nor a cold-start benchmark. Cold first load ~7 s, modest forecast improvement, five previously reported development dependency advisories, and optional P1 presentation deferrals remain documented limitations. Local acceptance is not public-production readiness.
