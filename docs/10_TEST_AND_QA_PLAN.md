# 10 — Test and QA Plan

**Related:** `05_ANALYTICS_MODELS.md` §13, §15, §16.1 (golden cases, invariants), `06_DATA_GENERATION.md` §11, `08_API_SPECIFICATION.md` §5, `09_IMPLEMENTATION_ROADMAP.md`

---

## 1. Strategy

### 1.1 Goals

1. Prove **data correctness** (integrity, reconciliation, no leakage).
2. Prove **analytical correctness** (formulas match hand calculations; invariants hold).
3. Prove **contract correctness** (API matches schemas; UI shows API values).
4. Prove **reproducibility** (same seed → same data → same outputs).
5. Prove the **demo works** end to end on a fresh setup.

### 1.2 Test pyramid

| Layer | Tool | Count (target) | Runs in `make verify` |
|-------|------|----------------|-----------------------|
| Analytics unit + property + golden | pytest | 120+ | yes |
| Generator unit | pytest | 15+ | yes |
| Database (constraints, DQ, views, SQL analyses, point-in-time) | pytest + Postgres | 60+ | yes |
| API | pytest + FastAPI TestClient + Postgres | 70+ | yes |
| Frontend unit | Vitest + RTL | 40+ | yes |
| E2E smoke | Playwright | 8 specs | `make e2e` (needs running stack) |
| Performance | scripts | — | Phase 8, manual |

### 1.3 Markers and environments

- `@pytest.mark.unit` — no DB.
- `@pytest.mark.db` — needs `TEST_DATABASE_URL`.
- `@pytest.mark.api` — needs DB + app.
- `@pytest.mark.slow` — standard-preset checks (excluded from default run; `pytest -m slow` in Phase 3/8).

### 1.4 Fixtures

- **Session fixture `loaded_small_db`:** migrates `stocgain_test` to head, applies views, generates the **small** preset with seed 42 into a temp directory, loads it, validates. Runs once per session (~20 s target).
- **Session fixture `analytics_small`:** runs `analytics backfill --weeks 4` + `run --evaluate` on the small DB.
- **Function fixture `db_tx`:** a connection inside a transaction rolled back after each test (for mutation tests like constraint violations and point-in-time deletion).
- **Golden fixtures:** `backend/tests/fixtures/golden_cases.json` (05 §15), `format_cases.json` (shared formatter cases, also copied to `frontend/tests/fixtures/`).
- **Neutral dataset:** some tests use `events.enabled = false` (generated into a separate temp dir) to avoid story effects.

### 1.5 Coverage targets

- `stocgain.analytics`: ≥ 85% line coverage (enforced with `--cov-fail-under=85` on that package).
- `stocgain.generator`: ≥ 75%.
- Others: no hard target; every endpoint has at least one success and one failure test.

---

## 2. Database tests (`tests/db/test_constraints.py`)

Each test attempts an invalid write inside `db_tx` and asserts the specific PostgreSQL error class (`IntegrityError` subclass / SQLSTATE).

| ID | Test | Expected |
|----|------|----------|
| DB01 | Insert `daily_sales` with unknown `store_id` | FK violation (23503) |
| DB02 | Insert PO line referencing unknown PO | FK violation |
| DB03 | Insert receipt referencing unknown PO line | FK violation |
| DB04 | Duplicate `products.sku` | unique violation (23505) |
| DB05 | Duplicate `(store_id, product_id, sales_date)` | PK violation |
| DB06 | `inventory_snapshots.closing_on_hand = −1` | check violation (23514) |
| DB07 | `products.unit_price <= unit_cost` | check violation |
| DB08 | `products.unit_price = 0` | check violation |
| DB09 | Second `is_primary = true` row for a product | unique violation (partial index) |
| DB10 | `purchase_orders.promised_delivery_date = order_date` | check violation |
| DB11 | `purchase_order_lines.quantity_cancelled > quantity_ordered` | check violation |
| DB12 | `inventory_adjustments.quantity_delta = 0` | check violation |
| DB13 | Shrink adjustment with positive delta | check violation |
| DB14 | `NULL` in a NOT NULL column (e.g., `products.product_name`) | not-null violation (23502) |
| DB15 | `min_order_qty` not a multiple of `case_pack_qty` | check violation |
| DB16 | Invalid enum value for `risk_tier` | invalid text representation (22P02) |
| DB17 | `inventory_risk_snapshots.stockout_probability = 1.2` | check violation |
| DB18 | `inventory_position_units ≠ on_hand + on_order` | check violation |
| DB19 | Recommendation `expedite_po` without `related_purchase_order_id` | check violation |
| DB20 | `no_action` recommendation with non-null `priority_rank` | check violation |
| DB21 | Two binding checkpoints for one position | unique violation (partial index) |
| DB22 | PO for a (supplier, store) pair with no lane | FK violation (composite) |
| DB23 | `dataset_manifest` second row (`dataset_id = 2`) | check violation |
| DB24 | Migration round trip: `upgrade head` → `downgrade base` → `upgrade head` on empty DB | succeeds |

---

## 3. Data-quality and generator tests

### 3.1 Data-quality checks (`tests/db/test_data_quality.py`)

- **Clean data:** every `error`-severity check DQ01–DQ18 (03 §10) returns 0 rows on the loaded small preset.
- **Detection:** for each of DQ01, DQ02, DQ03, DQ05, DQ06, DQ07, DQ09, DQ10, DQ11, DQ12, DQ15, corrupt one row inside `db_tx` (e.g., `UPDATE inventory_snapshots SET closing_on_hand = closing_on_hand + 1 WHERE …`) and assert the check returns exactly the corrupted row(s). This proves the checks work, not just that clean data passes.
- **Runner:** `stocgain data validate` exits 1 when any error check fails (CLI test with corrupted DB).

### 3.2 Generator tests

All tests in 06 §11. Additionally:

| Test | Assertion |
|------|-----------|
| Inventory balance reconciliation (in memory, all presets in parametrize: small only by default) | Equation holds for 100% of position-days |
| Negative inventory guard | No negative values in opening/closing; adjustments capped |
| PO relationships | Every line's product has the PO's supplier in `product_suppliers`; every receipt's line exists; received + cancelled ≤ ordered |
| Promotion overlaps | None |
| Calendar coverage | All fact dates within calendar range |
| Manifest | `content_checksum` equals recomputed SHA-256; `data_origin = synthetic` |

---

## 4. SQL tests

### 4.1 Views (`tests/db/test_views.py`)

| Test | Assertion |
|------|-----------|
| `mv_daily_position` row count | = stores × products × days |
| Availability status | Matches Python recomputation from `opening_on_hand`, receipts, sales for 100% of small-preset rows |
| `v_po_line_status.open_quantity` | ≥ 0 and = ordered − received − cancelled |
| `v_po_status.lead_time_days` | > 0 for all received POs |
| `v_inventory_reconciliation` | 0 rows with `discrepancy ≠ 0` |
| `v_stockout_episodes` | Σ `episode_days` per position = censored days |
| `v_category_dow_profile` | Per category, mean of `dow_index` = 1 (±1e−9) (after analytics run) |
| `v_product_abc_class` | Class A non-empty; largest-revenue product is A |
| `v_current_risk` | One row per position in current run; joins don't duplicate rows |
| `v_risk_trend` | One `as_of_date` per run date; counts sum to positions per run |

### 4.2 Analyses (`tests/db/test_sql_analyses.py`)

Parametrized over `sql/analyses/*.sql`: executes without error; returns the documented columns (compare to an expected-columns map); asserts the analysis-specific invariant from 04 §5 (e.g., `p50 ≤ p90`, `cumulative_share` ends at 1.0, `priority_rank` contiguous, ADI/CV² classification matches model for `clean_days ≥ 14`).

### 4.3 Point-in-time / leakage tests (`tests/db/test_point_in_time.py`)

For `as_of = history_end − 30`:

1. Run every `sql/pipeline/*.sql` (except latent) → results A.
2. Inside `db_tx`: delete all `daily_sales`, `inventory_snapshots`, `inventory_receipts`, `inventory_adjustments` rows dated after `as_of`, delete POs ordered after `as_of`, refresh the MV (in the transaction).
3. Re-run → results B. Assert A == B exactly.
4. Run the forecasting function on extracted data for `as_of` in both states → identical forecasts.

### 4.4 KPI SQL tests

- `overview_summary.sql` values equal independently written assertion queries (e.g., `SELECT COUNT(*) FROM v_current_risk WHERE risk_tier IN ('critical','high')`).
- Filters: for each store, Σ per-store `at_risk_positions` = chain total.

---

## 5. Forecast tests (`tests/unit/test_forecasting.py`, `test_backtest.py`)

| ID | Case | Expected |
|----|------|----------|
| F01 | Golden G4 (censored example) | `ℓ = 6.019 ± 0.002`, `σ_d = 2.453 ± 0.002`, `censored_days = 6`, naive 3.643 |
| F02 | All clean, constant 5/day, flat DOW | `ℓ = 5`, `σ_obs = 0`, `σ_d = √5` |
| F03 | Weekday effect: data = 10 × idx(dow) exactly | `ℓ = 10`; `f_t = 10 × idx` |
| F04 | Promo days in history excluded; future promo applies planned lift 1.35 | level unaffected by promo spike; `f_t = ℓ × idx × 1.35` on promo dates |
| F05 | 10 clean days | `method = blended`, `λ = 10/14` |
| F06 | 3 clean days, chain rate available | `method = chain_fallback`, `σ_obs = ℓ` |
| F07 | No clean days anywhere | `method = insufficient_data`, `ℓ = 0` |
| F08 | Zero sales on all clean days | `ℓ = 0`, `σ_d = 0`, pattern `no_demand` |
| F09 | Intermittent (5% non-zero days) | `ℓ ≈ mean`; pattern `intermittent` or `lumpy` per CV² |
| F10 | Missing day in the input grid (defensive) | treated as censored, warning logged, no crash |
| F11 | Horizon sums | `F_7 ≤ F_14 ≤ F_28`; equal to sums of daily |
| F12 | Extension beyond 42 days | equals mean of days 36–42 |
| F13 | Trend ratio with < 4 days in a part | NULL |
| F14 | Demand pattern thresholds at exact boundaries (ADI 1.32, CV² 0.49) | boundary assignment per 05 §3.9 (≤ / <) |
| F15 | Backtest origins | 8 origins for standard length; fewer when history short; last origin = T − 28 |
| F16 | Backtest leakage guard | Forecast at origin `o` unchanged when data after `o` is replaced with random values |
| F17 | Metrics with Σactual = 0 | WAPE and bias NULL; MAE defined |
| F18 | Observed basis excludes censored target days | count of observations = in-stock target days |
| F19 | Naive and seasonal naive definitions | match hand-computed small arrays |

---

## 6. Risk, policy, exposure, explanation, recommendation tests

### 6.1 Unit and golden tests

| ID | Case | Expected |
|----|------|----------|
| R01 | G1 hero | 05 §15 values |
| R02 | G2 receipt checkpoint | binding = receipt, values per 05 §15 |
| R03 | G3 NB slow mover | family NB, values per 05 §15 |
| R04 | G5 scenario | values per 05 §15 |
| R05 | G6 service level 98% | ROP 180, S 269, qty 180 |
| R06 | Days of cover | `OH=100, D̄=12 → 8.3`; `D̄=0 → None`; `OH=0 → 0`; cap 365 |
| R07 | Stockout probability boundaries | `μ=0 → 0`; `σ=0, μ>S → 1`; `σ=0, μ≤S → 0`; huge `S → 0`; result ∈ [0,1] |
| R08 | Very low inventory | `OH=1, μ=50 → P > 0.99`, tier critical |
| R09 | `OH=0`, `D̄>0` | tier critical, driver `currently_out_of_stock` |
| R10 | PO tomorrow (`w=0`) | receipt checkpoint `P=0` |
| R11 | Overdue PO ETA (G10, G11) | ETA per 05 §4.3 |
| R12 | Delayed supplier shipments: positive mean delay 1.6 → ETA = promised + 2 | |
| R13 | Multiple POs same ETA | combined into one checkpoint, supply summed |
| R14 | PO after window end | not a checkpoint; included in IP; "PO too late" expedite when `P ≥ 0.25` |
| R15 | No double counting | supply at window end = OH + POs before window end only; IP = OH + all POs |
| R16 | Lane fallback | `n < 8` → supplier; supplier `n < 8` → contract with σ = 0.25×contract |
| R17 | Safety stock Normal = `z σ` | exact |
| R18 | ROP integer ceiling with float noise (`μ+SS = 168.0000000001`) | 168 (uses `ceil(x − 1e−9)`) |
| R19 | Order quantity rounding | raw 157, pack 12 → 168; raw 5, MOQ 24 → 24; `S ≤ IP` → None |
| R20 | Zero-demand position | ROP = S = 0; `below_reorder_point = false` |
| R21 | Exposure | `E × λ × price`, `E × λ × margin`; never multiplied by `P` |
| R22 | Tier thresholds | P = 0.0999 → low; 0.10 → moderate; 0.10 with margin 250 → high; 0.25 → high; 0.50 → critical |
| R23 | `insufficient_data` | tier moderate, action monitor |
| R24 | Drivers | each driver rule at its threshold boundary |
| R25 | Explanation text | G1 explanation string matches 05 §8.3 exactly; numbers in text = formatted breakdown values |
| R26 | Recommendation rules | each branch of 05 §9.1 with a minimal fixture; `recommended_order_units` present with expedite when below ROP |
| R27 | Priority ranking | lexicographic order; deterministic tiebreak; contiguous ranks |
| R28 | Sensitivity | each counterfactual changes only its input; hero values 0.8970 / 0.7758 |
| R29 | Projection | never negative; stockout day per 05 §5.8; band ordering `low ≤ expected ≤ high` |

### 6.2 Property / invariant tests (`tests/unit/test_properties.py`)

Use deterministic grids or seeded random samples (no new dependency required). For each, 500 random cases with seed 7.

| Property | Classification (05 §16.1) |
|----------|---------------------------|
| `prob_exceeds` non-increasing in supply `S` | strict |
| `quantile` non-decreasing in `α` → ROP non-decreasing in service level | strict |
| Normal family: SS non-decreasing in `σ_d` and in `σ_L` | strict (Normal only) |
| Fixed family: `P` non-decreasing in lead time (no POs) | strict for fixed family |
| Fixed family: `P` non-decreasing in demand level | model-dependent → test only within one family |
| `expected_shortage ≥ max(0, μ − S)` (Jensen) | strict |
| `expected_shortage` non-increasing in `S` | strict |
| Projection non-negative | strict |
| `reorder_point ≤ order_up_to` | strict |

Aggregate (model-dependent) behavior is tested on the standard dataset in §6.3.

### 6.3 Scenario tests (`tests/unit/test_scenario.py`, `tests/api/test_scenarios.py`)

| ID | Case | Expected |
|----|------|----------|
| S01 | Neutral inputs | every position output equals stored snapshot (1e−6); `delta` all zero |
| S02 | `lead_time_change_days = +4` | aggregate margin at risk ≥ baseline; at-risk count ≥ baseline (small preset) |
| S03 | `demand_change_rate = +0.2` | aggregate at-risk ≥ baseline |
| S04 | `service_level 0.95 → 0.98` | safety stock value increases; annual expected shortfall decreases; near-term risk metrics unchanged |
| S05 | Buffer +50% | safety stock value × 1.5 (±rounding); near-term risk unchanged |
| S06 | Lead time −7 on short lanes | floored to 1; warning emitted |
| S07 | ETA shift negative | ETA ≥ T + 1 |
| S08 | Out-of-range (`lead_time_change_days = 15`, `service_level = 1.0`, `demand_change_rate = −0.6`, NaN) | 422 `VALIDATION_ERROR` |
| S09 | Empty scope (supplier with no products in scope intersection) | 200, `positions_in_scope = 0` |
| S10 | Unknown supplier ID | 422 `UNKNOWN_FILTER_VALUE` |
| S11 | Tier transition matrix sums | row sums = baseline tier counts; column sums = scenario tier counts |
| S12 | Cache invalidation | after a new current run, baseline reflects the new run |

---

## 7. API tests (`tests/api/`)

| File | Cases |
|------|-------|
| `test_health_meta.py` | health OK; DB down (monkeypatched engine) → `database: unavailable`; meta fields present; `run: null` when no run |
| `test_filters.py` | lists sorted; counts equal dims |
| `test_overview.py` | summary equals SQL assertions; prior-run delta; filters (store, region, category, combos); unknown filter ID → 422; distribution always 4 tiers; trend points = distinct as-of dates; heatmap dense; top products ordering |
| `test_recommendations.py` | ordered by rank; action filter; limit bounds |
| `test_risk_positions.py` | pagination (first, middle, beyond last, page_size bounds 0/201 → 422); every `sort_by` asc/desc stable; filter combinations (parametrized grid of store × category × tier × action × q × below_rop); `summary` equals SQL aggregate; `total_items` equals `COUNT(*)`; consistency with overview |
| `test_export.py` (P1) | CSV header, comment line, row count equals filtered total; content type |
| `test_positions.py` | detail schema; unknown store → `STORE_NOT_FOUND`; unknown product → `PRODUCT_NOT_FOUND`; inactive/missing snapshot → `POSITION_NOT_FOUND`; explanation equals stored; checkpoints include one binding; history length = `days`; projection stockout date = snapshot; PO list statuses |
| `test_suppliers.py` (P1) | list equals `v_supplier_performance`; detail 404; disclaimer present |
| `test_forecast_eval.py` (P1) | rows for 3 models × 2 bases; notes present |
| `test_scenarios.py` | S01–S12 |
| `test_errors.py` | unknown route → 404 envelope; forced exception → 500 envelope without traceback; analytics missing → 503 on analytics endpoints |
| `test_openapi.py` | every route has `response_model`; every numeric field has `x-unit`; schema exports deterministically |

---

## 8. Frontend tests

### 8.1 Unit (Vitest + RTL)

| Test | Assertion |
|------|-----------|
| `format.test.ts` | All shared `format_cases.json` cases; edge cases (`<0.1%`, `>99.9%`, compact USD, NULL days) |
| `KpiCard.test.tsx` | Renders value, Est. tag, delta polarity colors, tooltip text |
| `RiskTierBadge.test.tsx` | Label always present (not color-only) |
| `ProbabilityMeter.test.tsx` | Width proportional; text shown |
| `FilterBar.test.tsx` | Updates URL params; reset clears |
| `AssumptionControl.test.tsx` | Slider and input stay in sync; out-of-range input shows error and doesn't call `onChange` |
| `ComparisonGrid.test.tsx` | Δ and Δ% computed display; Δ% hidden when baseline = 0 |
| `client.test.ts` | Parses error envelope; maps 503 `ANALYTICS_NOT_READY` |

### 8.2 E2E (Playwright, against running stack with standard preset)

| Spec | Flow / assertions |
|------|-------------------|
| `overview.spec.ts` | Loads without console errors; 6 KPI values match `/overview/summary` response (intercept and compare); dataset badge visible; changing store filter updates URL and KPIs |
| `navigation.spec.ts` | Sidebar navigation to every implemented page; global filters persist; 404 page |
| `risk_monitor.spec.ts` | Tier filter → counts match API `summary`; sort by stockout probability desc → first row has max probability; search by SKU; pagination; back navigation restores state |
| `product_detail.spec.ts` | Drill down from Risk Monitor first row; explanation contains the same days-of-cover and probability strings as the breakdown panel; projection chart renders stockout marker when `projected_stockout_date` non-null; PO table renders |
| `scenario_lab.spec.ts` | Initial neutral results Δ = 0; set lead time +4 and demand +20% → at-risk increases; set service level 98% → safety stock value increases, near-term risk unchanged; reset → baseline; type invalid value → inline error, no request |
| `states.spec.ts` | Stub API at network layer (Playwright route) to return 503 → AnalyticsNotReady visible; 500 → ErrorState with retry (this is the only allowed use of fake responses: testing error states) |
| `responsive.spec.ts` | 1440, 1280, 390 widths: no horizontal page scroll; mobile menu opens; tables scroll within container |
| `a11y.spec.ts` (Phase 8) | axe: 0 serious/critical violations on each page |

### 8.3 State audit checklist (manual, Phase 8)

For each page: initial loading skeleton ✓ · empty state with next step ✓ · error state with retry ✓ · analytics-not-ready ✓ · tooltips on every KPI/column ✓ · Est. tags on estimates ✓ · no dead controls ✓ · keyboard navigation ✓.

---

## 9. End-to-end verification (fresh setup)

Script `scripts/verify_fresh_setup.sh` (Phase 9), run from a temporary clone:

```bash
set -euo pipefail
docker compose down -v || true
rm -rf data/generated
make setup
make db-up
time make pipeline             # migrate + seed standard + analytics
make verify                    # lint, typecheck, unit/db/api tests, openapi check
(make api > /tmp/api.log 2>&1 &) ; (make web > /tmp/web.log 2>&1 &)
for url in http://localhost:8000/api/v1/health http://localhost:3000; do
  for i in $(seq 1 60); do curl -sf "$url" > /dev/null && break; sleep 2; done
done
make e2e
```

Record: total time, `make pipeline` time, test counts, any failures — in `docs/PROGRESS.md`.

---

## 10. Performance benchmarks

| Benchmark | Method | Target (to be verified) | Assumptions |
|-----------|--------|-------------------------|-------------|
| Generate standard | `time stocgain data generate` | < 60 s | Apple Silicon, Python 3.12 |
| Load + validate + refresh standard | `time stocgain data load && validate && db refresh` | < 90 s | Docker Postgres with ≥ 4 GB |
| `make analytics` (13 runs + backtest) | `step_timings` | < 3 min | vectorized NumPy |
| API endpoints | `backend/scripts/bench_api.py` (20 sequential requests, p50/p95) | 08 §1.8 | warm DB |
| Key SQL queries | `make explain` | 04 §9.3 | warm cache |
| Scenario full scope | API timing field `computation_ms` | < 1.5 s p95 | cached baseline |
| Frontend | Playwright `performance.timing`, Overview to all widgets rendered | < 2.5 s on localhost | production build (`npm run build && npm start`) |

Rules: report measured numbers only; include machine description; if a target is missed, document cause and mitigation instead of adjusting the target silently.

---

## 11. Known modeling limitations (and how tests treat them)

| Limitation | Test treatment |
|-----------|----------------|
| Censored days assumed similar to clean days | Simulation-only evaluation quantifies residual bias; no test asserts "unbiased" |
| Max-of-checkpoints is a lower bound | Unit test documents it with a two-checkpoint case where union probability (Monte Carlo, seeded, 100k draws) ≥ max |
| Normal/count family switch at μ = 20 | Monotonicity tests restricted to a family; one test documents a small discontinuity at the switch |
| No annual seasonality | Backtest results reported per segment; LG bias expected and not hidden |
| Lost-sale rates are assumptions | Exposure tests check formula, not "realism" |
| Lead-time right-censoring | Documented; lane test asserts unreceived POs excluded from means but included in on-time denominator |
| Projection band approximate | Band ordering tested; coverage not claimed |

---

## 12. Quality gates

`make verify` = `ruff check` + `ruff format --check` + `mypy src/stocgain/analytics` + `pytest -m "unit or db or api"` with coverage gate + `npm run lint` + `npm run typecheck` + `npm run test` + `make check-openapi`.

A phase cannot be marked done in `docs/PROGRESS.md` unless `make verify` passes (and `make e2e` from Phase 6 onward).
