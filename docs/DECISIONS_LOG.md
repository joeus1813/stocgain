# Implementation decisions

## 2026-10-09 · Stage boundary and phase gates
Decision: Stage 1 means original phases 0–2, sequentially. Phase 0 includes only the temporary real-health page. No business API, forecasting, or dashboard is authorized here.
Reason: user request and docs/09 phase gates. Docker is absent; database-dependent gates cannot be claimed.
Alternatives: bypassing gates or replacing PostgreSQL with SQLite; rejected.
Impact: finish verifiable Phase 0 work and preserve remaining phases as unstarted if Docker remains unavailable.

## 2026-10-09 · Repository and tooling
Decision: initialize Git in the supplied workspace on stage-1-foundation; preserve the supplied specs in an initial commit. Install uv and Node 22 under ignored .tools for this session.
Reason: no repository or application existed; global uv/Docker and Node 22 are absent. Working in the supplied directory keeps the result accessible.
Alternatives: global installations or another checkout; unnecessary for the authorized bootstrap.
Impact: README requires normal uv/Node 22 installations; local tool paths are not committed.

## 2026-10-09 · Phase-specific verification
Decision: make verify runs lint/typecheck/test now; OpenAPI drift checking becomes required in Phase 4, as AGENTS.md §7 specifies. Future targets fail explicitly until implemented.
Reason: CODEX_HANDOFF's general make verify requirement predates business API generation; docs/09 Phase 0 only requires health and trivial tests.
Alternatives: silently succeeding stubs; rejected.
Impact: no false indication that later-phase commands work.

## 2026-10-09 · Health contract
Decision: /api/v1/health returns HTTP 200 with database unavailable when the connection fails, per docs/08 §3.1; analytics_ready=false and current_run_id=null in this pre-schema skeleton.
Reason: health is process liveness with explicit dependency status, not a business endpoint.
Alternatives: HTTP 503 on database outage; conflicts with normative health contract.
Impact: green process status must not be mistaken for database connectivity. Extend run detection when analytics tables/views exist.

## 2026-10-09 · Supporting development packages
Decision: use setuptools as the Python build backend; @tailwindcss/postcss + postcss, React/Node type packages, jsdom, and shadcn's clsx/tailwind-merge/class-variance-authority/tw-animate-css support the specified frameworks and tests.
Reason: packaging, Tailwind v4 processing, TypeScript, RTL DOM tests, and shadcn setup require this tooling.
Alternatives: hand-built substitutes; unnecessary maintenance.
Impact: no new product infrastructure or data service.

## 2026-10-09 · Test transport compatibility
Decision: constrain transitive Starlette to <1 while retaining current compatible FastAPI and the specified httpx test transport.
Reason: Starlette 1.7 emitted a deprecation warning requiring unlisted httpx2; the stable 0.x branch supports the selected stack without changing test infrastructure.
Alternatives: adding httpx2 or suppressing the warning; rejected.
Impact: exact compatible release is pinned in uv.lock; revisit with an explicit transport upgrade.
The same test-transport compatibility constraint includes AnyIO <4.12: newer AnyIO deprecates the BlockingPortal alias used by the compatible Starlette 0.x TestClient. No warnings are suppressed.

## 2026-10-09 · Frontend scaffolding
Decision: use the current create-next-app scaffold, remove demo content/branding and optional caching flags, use standard Tailwind v4 PostCSS integration. @next/env loads the root .env for native frontend commands.
Reason: Phase 0 needs only a real health client, consistent root environment, and documented setup. No product pages or remote font build dependency yet.
Alternatives: retain generated demo or duplicate environment files; rejected.
Impact: UI fonts/components remain Phase 5 work. @next/env is the framework's environment helper and is pinned with Next.

## 2026-10-09 · Dependency audit and shadcn setup
Decision: retain the Next-compatible lint dependency tree; document the unresolved development-only braces advisory (GHSA-vfj7-8cjw-p6xm, propagated through micromatch/fast-glob). Registry's latest braces is 3.0.3, which is affected; do not force-downgrade Next to 14 as npm suggests.
Reason: no compatible upstream patch exists. ESLint 9 remains compatible with Next's React/import plugins; package manager reports it as unsupported.
Alternatives: forced major framework downgrade or overriding incompatible lint peers; rejected.
Impact: five high advisory entries in development tooling; recheck upstream before presenting the repository as complete. No production deployment is in scope.

Decision: configure shadcn manually (components.json and standard cn utility) with Tailwind v4 and existing tokens, following the documented manual installation path.
Reason: current init defaults to additional preset components/styles beyond the Phase 0 health page; preserve the required product tokens and avoid unrelated UI.
Impact: shadcn components themselves are not built until their feature phase.

## 2026-10-09 · Review fixes and browser isolation
Decision: force Next's root environment reload with the actual development/production phase flag. A regression simulates Next's prior environment cache and asserts a root-only API URL is loaded.
Reason: independent review reproduced ignored root settings; observed regression failed with undefined before the fix and passed after.
Impact: custom root .env API settings now propagate; no product behavior change.

Decision: Playwright resolves localhost to IPv4, matching Compose's localhost publication.
Reason: an unrelated pre-existing application listens on ::1:3000, while this session's Next server is reachable at 127.0.0.1:3000. Initial browser test reached the unrelated app. Its process was not modified or stopped.
Impact: browser smoke tests select this stack's IPv4 address while preserving localhost origin/CORS.

Deferred review minor: environment-provided analytics_config_path and generator_config_path remain relative; normalize against REPOSITORY_ROOT before Phase 1 consumes them. Both configs are unused in Phase 0.

## 2026-10-09 · Owner-directed rebrand and database preservation
Decision: rename the product to `stocgain.` (Predictive Retail Inventory Intelligence Platform; “Predict stockouts. Replenish smarter.”), Python package/CLI to `stocgain`, and npm package to `stocgain-web`. Update design references and OpenAPI metadata. Keep the active root checkout path unchanged.
Reason: explicit owner request; root path is controlled by the active Codex workspace.
Alternatives: global blind text replacement or root directory rename; rejected because they would alter business language or disrupt the checkout.
Impact: existing Docker project/volume, PostgreSQL database/user/password `stocksense`, and `stocksense_test` remain as compatibility identifiers. Compose explicitly pins `name: stocksense` so future checkout naming cannot silently create a second volume/database. `STOCKSENSE_ENV` remains an accepted legacy environment alias; `STOCGAIN_ENV` is preferred. No database or volume was deleted or renamed.

## 2026-10-09 · Docker access and Phase 0 gate
Decision: use `/Applications/Docker.app/Contents/Resources/bin/docker` on PATH and approved local socket/TCP access. Keep the same PostgreSQL 17 service and host port 5433.
Reason: the Docker executable was installed but absent from the shell PATH; default sandbox blocked the socket and localhost until local permission was granted. No Docker reinstall was needed.
Alternatives: a second database or changing ports; rejected.
Impact: Phase 0 acceptance was re-run against PostgreSQL 17.11 in the existing Compose project; results recorded in PROGRESS.md.

## 2026-10-10 · Phase 1 implementation and safe loading
Decision: mirror the four applied revisions in explicit SQLAlchemy table/model declarations; retain migration history. Implement the small/standard simulator and required Phase 1 reconciliation view only. Normalize generator config paths against the repository root.
Reason: preserve the verified schema and phase boundaries. PostgreSQL metadata comparison and schema-dump table-definition comparison pass; the ERD remains unchanged.
Alternatives: redesigning tables, editing applied revisions or implementing all Phase 2 views now; rejected.
Impact: no new dependency or schema revision; optional large preset remains an explicit unsupported operation.

Decision: default loading is non-destructive: verify files, no-op/revalidate identical content, refuse different content. Explicit `--replace` transactionally truncates application rows, COPY-loads, validates and rolls back on errors.
Reason: owner prohibited unapproved database resets. Existing test DB uses small data and main DB uses standard data; no database/volume was recreated. The roadmap's `make db-reset` verification command was intentionally not used.
Alternatives: unconditional truncation or another database; rejected.
Impact: after price regression repair, automatic approval initially blocked standard replacement; owner subsequently authorized continuation. Created a custom-format backup, checked `pg_restore --list`, then reloaded successfully. Existing DB/schema/volume identifiers are unchanged. Recovery file is ignored at `data/backups/pre-phase1-corrected-reload.dump`.

Decision: execute DQ/profile queries with transaction-local parallel workers disabled.
Reason: the standard profile exhausted Docker's 64 MB shared-memory mount with parallel workers. Serial execution passed against the unchanged dataset.
Alternatives: changing Docker storage or loosening checks; rejected.
Impact: bounded local resource use; check semantics unchanged. Runtimes are recorded in PHASE1_VERIFICATION.md.

## 2026-10-10 · Generator corrections and calibration interpretation
Decision: enforce .97/.98/.99 price points inside configured bounds and reserve pinned demo supplier names before randomly choosing other names.
Reason: standard seed 42 exposed four integer-price lower-bound clamps; seed 89 exposed a duplicate pinned supplier name. Regression tests reproduce the cases and pass after correction.
Alternatives: editing output CSVs, changing seed or dropping uniqueness; rejected.
Impact: corrected standard checksum recorded in PHASE1_VERIFICATION.md. Final generation remains deterministic; small seed 42 checksum unchanged.

Decision: retain docs/06 §7 fulfillment probabilities and record two §10 plausibility deviations rather than silently tune product behavior. This uses docs/09 Phase 1's explicit allowance for explained calibration deviations.
Reason: the early branch has probability 0.08, followed by on-time when u < 0.08 + p_s. Thus early-or-on-time probability is min(1, 0.08 + p_s), not p_s alone. Standard median 90-day supplier OTR is 0.977102 (target 0.80–0.92). Demo Plumbing p_s=0.70 gives theoretical 0.78 early-or-on-time before finite sampling and cutoff censoring; observed received-PO 90-day OTR is 0.819355 (target <0.80). Conditioning on received POs excludes some late unreceived orders at the endpoint. The prescribed small-preset event unit test still passes its <0.80 assertion; it has not been weakened.
Alternatives: lowering p_s below prescribed settings or changing the early/ontime branch; rejected because exact simulation rules take precedence over approximate calibration expectations.
Impact: operational DQ is clean. Supplier rankings and downstream recommendation outcomes are not guaranteed or claimed before their later-phase verification. No generated rows were edited by hand.

Decision: follow the explicit promotion cadence over burn-in, history and future-planning horizon, rather than the approximate supporting-volume estimate.
Reason: 8 categories × approximately 257/15 starts implies about 137 promotions plus scheduled events; actual standard count is 143 versus the rough 70–90 estimate. Receipts are 55,583 versus approximate 60k–75k, consistent with 55,415 lines, partial shipments and unreceived orders at cutoff.
Alternatives: arbitrary extra receipts or fewer promotion events to match approximate counts; rejected.
Impact: all 18 DQ checks and required dense counts pass. These are documented plausibility differences, not hidden acceptance failures. Post-analytics risk calibration remains outside Phase 1.


## 2026-10-11 · Phase 2 SQL implementation and historical correctness
Decision: preserve exactly 12 views, 15 standalone analyses and 11 pipeline extraction queries. Reuse the Phase 1 reconciliation view and applied migrations. No physical-table change, second database, generator retuning or forecasting implementation.
Reason: explicit Phase 2-only scope. Model-dependent views execute empty in the project DB; rollback-only SQL fixtures exercise joins, rankings and KPIs. Actual forecast comparisons remain marked requires_run for Phase 3.
Alternatives: generating fake production risk rows or beginning forecasting; rejected.
Impact: Stage 1 SQL readiness does not claim model accuracy, dashboard readiness or populated-model performance.

Decision: correct executable SQL to its documented intent: cast REGR_SLOPE to numeric before ROUND, guard zero position counts, return NULL for absent prior run, and keep current-run supplier views empty without a current run.
Reason: the prose contracts and edge-case rules conflict with these omissions in the sample SQL. Tests reproduced missing-prior and empty-run failures before fixes.
Impact: no formula, threshold or object-name change; docs/04 examples synchronized.

Decision: bound supplier-view receipt aggregation and PO dates by the selected current run's as-of date, rather than using lifetime v_po_status directly.
Reason: the historical regression failed: future first receipts hid overdue POs, changed in-full counts and contaminated lead-time summaries. The owner explicitly requested correction of historical receipt leakage. Local receipt/PO CTEs preserve the documented KPI definitions while enforcing the cutoff.
Alternatives: documenting leakage as a permanent limitation or adding more global views; rejected.
Impact: no extra views or changed end-of-history definitions. Historical fixture removes future receipts/POs in a rolled-back transaction; both supplier views must remain identical. Lifetime PO views remain intentionally lifetime views for descriptive history-end analyses.

Decision: chain fallback SQL computes mean deseasonalized clean demand (z), including full-history sufficient aggregates, and applies the whole-category flat profile for missing/<30-observation weekdays.
Reason: docs/05 §§3.4–3.6 give the exact formula, while docs/04's inventory summary only said mean clean units. Preserve the more explicit formula and future engine compatibility. Independent review identified the sparse-profile omission; nonzero sparse/missing-weekday tests failed then passed after correction.
Impact: the category reporting extractor remains raw indices + observation counts; the later model must apply the same documented effective-profile rule. No forecasting engine implemented.

Decision: retain normative analysis 14's observed chain units for XYZ and analysis 03's descriptive coverage buckets; correct contradictory descriptive sentences in docs/04.
Reason: executable normative SQL was explicit; prose had incorrectly called XYZ clean-day and claimed a forecast comparison absent from that query.
Impact: labels now describe delivered data. No numerical behavior altered.

Decision: use existing prescribed MV unique/date indexes and record serial PostgreSQL plans. No additional index migration is justified by current measurements.
Reason: the standard workload fits the existing architecture; serial execution avoids the previously observed Docker shared-memory limit. Q1 explains the MV SELECT and separately times actual REFRESH, because PostgreSQL does not EXPLAIN REFRESH directly.
Impact: timings are local third-run warm measurements; Q4/Q7/Q8 empty-run plans do not establish populated-model targets. Eight required workloads plus two direct-ops comparison wrappers are retained.

## 2026-10-12 · Phase 3 model implementation

Decision: preserve full precision through forecasting and policy calculations; apply PostgreSQL Numeric precision only at final snapshot serialization. Neutral scenario tests compare every serialized field to actual stored rows (including drivers/explanation), never recompute policy from rounded daily/lane values.
Reason: the neutral 1e-6 invariant and the specified numeric column scales otherwise conflict. No formula or schema changes.

Decision: the specific insufficient-history rule in docs/05 §3.6/E15 takes precedence over generic first-match action rules in §9.1. An insufficient_data forecast always produces monitor, including with overdue POs. A regression reproduces this case.

Decision: retain the generator and risk thresholds despite calibration advisory. Actual current tiers: 727 critical (15.15%), 331 high (6.90%), 322 moderate, 3,420 low; critical+high 22.04%, above the 1–5% / 4–12% plausibility targets. These are forward-looking uncertain-window probabilities under the specified count/Normal model and scheduled receipts, rather than historical observed stockout rates. All exact golden calculations, constraints and persisted neutrality pass. No generated data or model formula is tuned to manufacture the target. The synthetic risk population is more elevated than the design's heuristic target; report that limitation with outputs.

Decision: explicit per-position orchestration around vectorized forecasting and SciPy primitives preserves traceable checkpoint logic. Actual neutral 4,800-position scenario time is 6.837 seconds, above the 1.5-second API target; performance optimization remains for Phase 4 validation. Standard initial 13-run execution recorded 150.050 seconds, below the three-minute batch target.

## 2026-10-13 · Phase 4 completion decisions

Retain all 16 required P0 endpoints and leave six P1 endpoints absent, as explicitly allowed by docs/09 Phase 4. No substitute or mock endpoints. The existing minimal six-KPI page is only the Phase 4 vertical slice; no Stage 3 frontend implementation.

Use named SQL files through a request-scoped Context with a read-only repeatable-read connection and one current-run identity. Full-precision scenario/projection inputs are cached by database and immutable run ID (bounded to two runs), rather than reconstructing policy from rounded stored forecasts. This preserves integer policy and neutral snapshot equivalence; cold cache population is visible in timings.

Profiling identified repeated construction of frozen SciPy distributions (14,897 objects, including their docstrings) and scanning all promotions once per position as the main scenario overhead. Replace frozen objects with the same SciPy distribution methods, use the equivalent Normal special functions, and index promotions by position. Keep the prescribed finite-sum count shortage and tail cutoff; independent finite-sum regression, golden cases and stored-neutral tests pass. No mathematical assumptions changed. Standard warm scenario p95 is 1.794 seconds (previous single neutral computation 6.837 seconds). The 1.5-second target remains unmet; cold baseline replay was 6.432 seconds, also above the 3-second target. These performance gaps are documented rather than concealed.

Run PostgreSQL tests in a single pytest process. Concurrent session fixtures previously deadlocked while applying repeatable views; those failed setup runs did not establish test success. Final acceptance is serialized.

### 2026-10-13 · Stage 3 scope and execution
Owner explicitly authorized Phases 5–7 and all six pages including Methodology and supplier analytics. This supersedes the previous handoff prohibition on Stage 3. Use the existing branch, one agent, no new worktree or delegated review, preserving all backend/data. Methodology and persisted forecast evaluation are included now to satisfy the explicit page request; no deployment or broader Stage 4 work. Build native accessible controls with existing dependencies and design tokens; TanStack Table remains server-controlled. Existing Stage 2 scenario latency is handled with retained results, cancellation and visible recalculation states, without changing mathematics.

### 2026-10-13 · Display boundary and CSV contract
Persisted Stage 2 prose uses one-decimal percentages, while binding UI rules require `<0.1%` / `>99.9%` for nonzero tails. Normalize only the probability token at the detail API serialization boundary using the shared Python formatter and API precision; leave database prose and every formula/output unchanged. This makes the explanation match the detail panel without rerunning the model. CSV has a documented text/csv response rather than a JSON Pydantic model; the OpenAPI contract test now verifies that explicit media contract and retains description/unit checks for every JSON field. Recharts entry animations disabled to respect the minimal-motion design and make visual verification deterministic.

2026-10-13 · Owner requested local frontend port 3050 because 3000 is occupied. Updated npm launch scripts, browser tooling, backend CORS and Compose host mapping; container-internal port stays 3000. Existing datasets and other port-3000 processes are preserved.

2026-10-13 · Owner authorizes Stage 3 latency remediation and Stage 4, superseding prior handoff restrictions; port 3050 checkpoint 61eb8d7 is retained. Single-agent work, no external publication or destructive data operations. Profile identifies scalar SciPy validation/inverse CDF work as the warm bottleneck. Count shortages use the existing batch engine's algebraically equivalent truncated first moment and public special-function tails; singular near-Poisson NB cases retain the original finite sum. Independent SciPy finite-sum/cap-boundary fixtures protect reference behavior.

2026-10-13 · Phase 8 uses @axe-core/playwright as a development-only dependency for the approved accessibility gate (docs/09); no runtime dependency added. Typography is enlarged through shared CSS tokens; page structure and analytical formulas remain unchanged. Destructive clean-setup instructions are superseded by the owner restriction: never remove an existing volume or dataset.
