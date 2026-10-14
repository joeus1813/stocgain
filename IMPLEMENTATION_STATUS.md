# stocgain implementation status

Updated 2026-10-14 (America/New_York).

**Stage 3 functional and warm Scenario Lab latency gates pass. Stage 4 implementation/presentation work is substantially delivered, but final acceptance remains open: the isolated fresh-clone setup/pipeline verification has not been run successfully. Do not claim the entire project is fully accepted.**

The current session preserves owner-created checkpoint `846e292`, the earlier `61eb8d7` port-3050 configuration, all project history, PostgreSQL data and model formulas. No remote changes, public deployment, purchases or data deletion were performed by this execution.

## Completed

- All six analytical screens, supplier detail and 22 API endpoints remain implemented with real PostgreSQL/model results.
- Scenario performance: replaced repeated scalar inverse-CDF work with equivalent count-tail/first-moment computations; preserved the original finite sum at numerically singular NB/Poisson boundaries. Golden/reference/scenario group: 43 passed in the implementation session.
- Actual warm browser benchmark: **p95 1,382.796 ms**, median 1,330.588 ms, 20 distinct 4,800-position updates including unchanged 400 ms debounce. Cold first page/model load: **7,014.114 ms**. Warm target passes; cold loading remains a documented limitation. Raw: `docs/perf/raw/stage4_scenario.json`.
- Readability: body 15px, title 28px, card headings 18px, minimum labels 12px, stronger muted-text/heatmap contrast. Corrected KPI description-list markup and added keyboard access to scrolling tables/formulas and a mobile dataset-badge accessible name.
- Desktop/mobile screenshots; five-width responsive check (1440/1280/1024/768/390), error/retry checks, forecast findings, README architecture, third-party notices, two-minute demo, resume drafts and publication/deployment preparation.

## Final verification actually executed

- First suite attempt encountered a stopped Docker daemon and was interrupted. Docker Desktop and the existing PostgreSQL service were started; no data was replaced.
- Healthy-DB comprehensive backend run: **268 passed, 2 failed**, 88.04 s; all 270 tests selected including slow standard-data tests; analytics coverage **92%**. Both failures expected port 3000 after the authorized change to 3050. Corrected the stale test origins; affected smoke group **11 passed** (1.00 s). Full backend suite was not repeated after that test-only fix.
- Final `make lint typecheck test-frontend check-openapi`: passed, **38 frontend tests**, 1.20 s; Ruff, mypy, ESLint, TypeScript and generated API drift checks clean. Production build passed.
- Full browser run: **12 passed, 2 failed** (1.2 min); failures identified missing keyboard scroll focus/mobile provenance name and an incorrect expected empty-search heading. After fixes, affected browser tests **5 passed in 33.0 s**; axe reports zero serious/critical violations on six primary screens plus supplier detail at desktop/mobile widths.
- Data validation: **all 18 DQ checks zero**, 9.022 s.
- `backend/scripts/verify_models.py`: succeeded; all **4,800** neutral position snapshots match stored values at canonical serialization precision, all aggregate neutral deltas zero. Current run 14 has 201,600 daily forecasts, 7,206 checkpoints and 72 evaluation rows. Measured neutral calculation 0.910 s; recorded pipeline duration is historical, not a new pipeline run.

## Remaining limitations and readiness

- Isolated fresh-clone `make setup → make pipeline → make verify → build` remains unexecuted; `scripts/verify_fresh_setup.sh` is prepared but not claimed verified. Existing data must not be deleted to test this.
- Cold Scenario Lab replay still takes about seven seconds; UI exposes loading and keeps previous results while updating.
- Optional compact-table density toggle and extra chart-data tables are deferred to avoid nonessential scope expansion; current tables and position observed-data disclosure remain functional.
- Full Compose application image profile/public hosting is unverified. The MIT license owner placeholder needs owner attribution before publication. Existing five high development dependency advisories remain unresolved; no forced incompatible update was applied.
- Forecast improvement is modest: observed WAPE 57.66% versus naive 58.39% (0.73 percentage points); erratic-demand performance is worse. No business-benefit or real-retailer accuracy claim.

See [Stage 4 report](docs/STAGE4_VERIFICATION.md), [forecast findings](docs/FORECAST_FINDINGS.md), [demo/resume drafts](docs/INTERVIEW_DEMO.md), [publication instructions](docs/PUBLICATION_AND_DEPLOYMENT.md). Local launch: `make db-up`, `make api`, `make web`; frontend http://localhost:3050. Remote publication still requires explicit owner approval.
