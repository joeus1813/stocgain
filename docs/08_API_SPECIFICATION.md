# 08 — API Specification

**Framework:** FastAPI + Pydantic v2 · **Base URL:** `http://localhost:8000/api/v1` · **Format:** JSON (UTF-8), except one CSV export
**Related:** `07_UI_UX_SPECIFICATION.md` §18 (page → endpoint matrix), `04_SQL_ANALYTICS.md` §6–7 (SQL sources), `05_ANALYTICS_MODELS.md` (definitions)

All example payloads are **illustrative** (they reuse the worked examples from 05 §13 and placeholder aggregates); real values come from the database at runtime.

---

## 1. Conventions

### 1.1 General

- All endpoints are read-only `GET` except `POST /scenarios/evaluate` (stateless computation; writes nothing).
- No authentication (single demo user, local only). CORS allows origins in `API_CORS_ORIGINS`.
- Endpoints are synchronous `def` functions (ADR-002).
- Every analytics response is scoped to **one run**: the current run resolved at the start of the request (`analytics.v_current_run`). All queries in the request bind that `run_id`.

### 1.2 Response headers

| Header | Value |
|--------|-------|
| `X-Request-ID` | Echoed from request or generated UUID4 |
| `X-StockSense-Run-Id` | Current run ID (analytics endpoints) |
| `X-StockSense-As-Of` | As-of date of that run |

### 1.3 Field naming and units

- `snake_case` fields. Suffixes declare units: `_usd` (US dollars, 2 decimals), `_units` (product units), `_days` (days), `_rate` / `_probability` / `service_level` (0–1 ratios), `_date` (ISO date), `_at` (ISO 8601 UTC timestamp).
- Every Pydantic field has `description=` (definition) and, for numeric fields, `json_schema_extra={"x-unit": "usd" | "units" | "days" | "ratio" | "units_per_day" | "count"}`. These appear in OpenAPI and in generated TS types' JSDoc.
- Rounding in responses: money 2 decimals; probabilities/rates 4 decimals; days 1 decimal (2 for lead-time stats); units/day 2 decimals; unit quantities integers except forecasts/expected values (2 decimals).
- `null` means "not applicable / unknown" and is documented per field (e.g., `days_of_cover` is `null` when forecast demand is 0).

### 1.4 Filters (shared)

Repeated query parameters (FastAPI `list[int]`), e.g. `?store_id=1&store_id=3`:

| Param | Type | Applies to |
|-------|------|-----------|
| `region_id` | int, repeatable | positions via store region; POs via store |
| `store_id` | int, repeatable | positions, POs |
| `category_id` | int, repeatable | positions via product; supplier KPIs via supplier primary category |
| `supplier_id` | int, repeatable | positions via primary supplier (where noted) |

Unknown IDs → **422** `UNKNOWN_FILTER_VALUE` with `details: {"param": "store_id", "values": [99]}`. Empty result sets are **200** with zeros/empty arrays.

### 1.5 Pagination (list endpoints)

Query: `page` (int ≥ 1, default 1), `page_size` (int 1–200, default 50). Response envelope:

```json
{ "items": [ … ], "page": 1, "page_size": 50, "total_items": 83, "total_pages": 2 }
```

`page` beyond `total_pages` returns `items: []` with correct totals (not an error).

### 1.6 Sorting

`sort_by` (enum per endpoint), `sort_dir` (`asc` | `desc`). Server applies a stable tiebreak `store_id, product_id`. Unknown `sort_by` → 422.

### 1.7 Error envelope and codes

```json
{ "error": { "code": "POSITION_NOT_FOUND", "message": "No position for store_id=3, product_id=9999 in run 14.", "details": { "store_id": 3, "product_id": 9999, "run_id": 14 } } }
```

| HTTP | `code` | When |
|------|--------|------|
| 400 | `EXPORT_TOO_LARGE` | CSV export would exceed 10,000 rows |
| 404 | `NOT_FOUND` | Unknown route |
| 404 | `STORE_NOT_FOUND`, `PRODUCT_NOT_FOUND`, `SUPPLIER_NOT_FOUND` | Path ID does not exist |
| 404 | `POSITION_NOT_FOUND` | Store and product exist but no risk snapshot in the current run |
| 422 | `VALIDATION_ERROR` | Pydantic validation failure; `details.errors` = list of `{loc, msg, type}` |
| 422 | `UNKNOWN_FILTER_VALUE` | Filter references unknown IDs |
| 503 | `ANALYTICS_NOT_READY` | No succeeded `current` run; `details.hint = "Run: make analytics"` |
| 503 | `DATABASE_UNAVAILABLE` | Connection failure |
| 500 | `INTERNAL_ERROR` | Unhandled exception (logged with request ID; generic message) |

FastAPI's default 422 body is replaced by the envelope via a custom `RequestValidationError` handler.

### 1.8 Performance expectations (standard preset, local laptop, warm DB; targets to be measured in Phase 8)

| Class | p95 target |
|-------|-----------|
| Metadata and filters | < 50 ms |
| Overview widgets | < 300 ms each |
| Risk positions page | < 150 ms |
| Position detail endpoints | < 150 ms each |
| CSV export (≤ 4,800 rows) | < 1 s |
| Scenario evaluate (all 4,800 positions) | < 1.5 s (first call per run may add cache warm-up < 3 s) |

### 1.9 Type generation for the frontend

1. `make openapi` runs `uv run python -m stocksense.api.export_openapi frontend/openapi.json` (imports `create_app()`, calls `app.openapi()`, writes JSON with sorted keys — no server needed).
2. Then `npm run gen:api` → `openapi-typescript openapi.json -o src/lib/api/schema.ts`.
3. Frontend code imports `components["schemas"]["OverviewSummary"]` etc. via aliases in `src/lib/api/types.ts`.
4. `make check-openapi` regenerates into a temp file and fails if it differs from the committed `schema.ts` (prevents drift).
5. Pydantic response models set `model_config = ConfigDict(extra="forbid")`; every route declares `response_model`.

---

## 2. Endpoint index

| # | Method | Path | Priority | Source |
|---|--------|------|----------|--------|
| 1 | GET | `/health` | P0 | `SELECT 1`, `v_current_run` |
| 2 | GET | `/meta` | P0 | `dataset_manifest`, `analytics_runs`, config |
| 3 | GET | `/filters` | P0 | dims |
| 4 | GET | `/overview/summary` | P0 | `api/overview_summary.sql` |
| 5 | GET | `/overview/risk-distribution` | P0 | `api/risk_distribution.sql` |
| 6 | GET | `/overview/risk-trend` | P0 | `api/risk_trend.sql` (`v_risk_trend`) |
| 7 | GET | `/overview/store-comparison` | P0 | `api/store_comparison.sql` |
| 8 | GET | `/overview/category-heatmap` | P0 | `api/category_heatmap.sql` |
| 9 | GET | `/overview/top-products` | P0 | `api/top_products.sql` |
| 10 | GET | `/recommendations` | P0 | `api/recommendations.sql` (`v_current_risk`) |
| 11 | GET | `/risk/positions` | P0 | `api/risk_positions.sql` (`v_current_risk`) |
| 12 | GET | `/risk/positions/export.csv` | P1 | same as 11 |
| 13 | GET | `/positions/{store_id}/{product_id}` | P0 | `api/position_detail.sql`, `api/position_checkpoints.sql` |
| 14 | GET | `/positions/{store_id}/{product_id}/history` | P0 | `api/position_history.sql` |
| 15 | GET | `/positions/{store_id}/{product_id}/projection` | P0 | `api/position_projection_inputs.sql` + `analytics.risk.project_inventory` |
| 16 | GET | `/positions/{store_id}/{product_id}/purchase-orders` | P0 | `api/position_purchase_orders.sql` |
| 17 | GET | `/positions/{store_id}/{product_id}/sensitivity` | P1 | scoring inputs + `analytics.risk.sensitivity` |
| 18 | GET | `/suppliers/summary` | P1 | `api/suppliers_summary.sql` |
| 19 | GET | `/suppliers` | P1 | `api/suppliers_list.sql` (`v_supplier_performance`) |
| 20 | GET | `/suppliers/{supplier_id}` | P1 | `api/supplier_detail_*.sql` |
| 21 | GET | `/forecasts/evaluation` | P1 | `forecast_evaluations` |
| 22 | POST | `/scenarios/evaluate` | P0 | `services/scenarios.py` → `analytics.scenario.evaluate` |

---

## 3. Endpoint specifications

### 3.1 `GET /health`

No params. Always 200 if the process is up.

```json
{ "status": "ok", "database": "ok", "analytics_ready": true, "current_run_id": 14, "version": "1.0.0" }
```

`database: "unavailable"` and `analytics_ready: false` are reported in the body (still 200) so the frontend can show a precise message.

### 3.2 `GET /meta`

Dataset provenance, current run, and model parameters (used by the shell, Methodology, and Scenario Lab defaults).

```json
{
  "dataset": {
    "data_origin": "synthetic",
    "label": "Simulated Retail Dataset",
    "provenance_statement": "Simulated Retail Dataset. All stores, products, suppliers, … not evidence about real retail operations.",
    "generator_version": "1.0.0",
    "preset": "standard",
    "seed": 42,
    "history_start_date": "2026-04-04",
    "history_end_date": "2026-09-30",
    "row_counts": { "daily_sales": 864000, "inventory_snapshots": 864000, "purchase_orders": 18102 },
    "counts": { "stores": 12, "regions": 4, "products": 400, "suppliers": 48, "categories": 8 },
    "events": [ { "id": "E1", "name": "Southeast storm-prep surge", "description": "…" } ]
  },
  "run": {
    "run_id": 14, "run_type": "current", "as_of_date": "2026-09-30",
    "model_version": "stocksense-baseline-1.0",
    "completed_at": "2026-10-09T19:05:21Z",
    "backfill_runs_available": 12
  },
  "parameters": {
    "service_level": 0.95, "review_period_days": 7, "lookback_days": 56, "half_life_days": 14,
    "min_clean_days_full": 14, "min_clean_days_blend": 7, "normal_min_mean_units": 20,
    "tier_thresholds": { "critical": 0.50, "high": 0.25, "moderate": 0.10 },
    "exposure_escalation_usd": 250.0, "carrying_cost_rate_annual": 0.25,
    "lost_sale_rates": { "Power Tools": 0.50, "Hand Tools": 0.40, "Electrical": 0.55, "Plumbing": 0.65,
                         "Building Materials": 0.70, "Lawn & Garden": 0.60, "Paint": 0.45, "Hardware": 0.35 },
    "scenario_limits": { "lead_time_change_days": [-7, 14], "demand_change_rate": [-0.5, 1.0],
                         "service_level": [0.80, 0.995], "safety_stock_buffer_rate": [-0.5, 1.0] }
  }
}
```

Errors: 503 `ANALYTICS_NOT_READY` is **not** raised here; `run` is `null` when no run exists (so the shell can render the not-ready state). Dataset missing → `dataset: null`. Cached per `run_id`.

### 3.3 `GET /filters`

```json
{
  "regions":    [ { "region_id": 1, "region_code": "SE", "region_name": "Southeast" } ],
  "stores":     [ { "store_id": 3, "store_code": "S03", "store_name": "Tampa Westshore", "region_id": 1 } ],
  "categories": [ { "category_id": 4, "category_code": "PL", "category_name": "Plumbing" } ],
  "suppliers":  [ { "supplier_id": 21, "supplier_code": "SUP-021", "supplier_name": "Gulfmark Plumbing Supply Co.", "category_id": 4 } ]
}
```

Sorted by code. Cached.

### 3.4 `GET /overview/summary`

Query: `region_id*`, `store_id*`, `category_id*`.

```json
{
  "as_of_date": "2026-09-30",
  "run_id": 14,
  "active_positions": 4800,
  "active_skus": 400,
  "at_risk_positions": 83,
  "critical_positions": 21,
  "at_risk_rate": 0.0173,
  "prior_at_risk_positions": 71,
  "at_risk_positions_change": 12,
  "gross_margin_at_risk_usd": 48213.55,
  "revenue_at_risk_usd": 141902.10,
  "median_days_of_cover": 31.4,
  "supplier_on_time_rate": 0.8791,
  "supplier_pos_due": 1604,
  "supplier_on_time_window_days": 90,
  "in_stock_rate": 0.9362,
  "in_stock_rate_prior": 0.9441,
  "in_stock_window_days": 28
}
```

- `prior_*`/`*_change` are `null` if no run exists for `as_of_date − 7`.
- `supplier_on_time_rate` is `null` if `supplier_pos_due = 0`.
- Source: 04 §6.1. Performance: < 300 ms.

### 3.5 `GET /overview/risk-distribution`

Query: global filters.

```json
{
  "tiers": [
    { "risk_tier": "critical", "positions": 21,   "share_of_positions": 0.0044, "margin_at_risk_usd": 31002.40 },
    { "risk_tier": "high",     "positions": 62,   "share_of_positions": 0.0129, "margin_at_risk_usd": 12404.75 },
    { "risk_tier": "moderate", "positions": 240,  "share_of_positions": 0.0500, "margin_at_risk_usd": 4101.20 },
    { "risk_tier": "low",      "positions": 4477, "share_of_positions": 0.9327, "margin_at_risk_usd": 705.20 }
  ],
  "total_positions": 4800
}
```

Always returns all four tiers (zeros included), ordered critical → low.

### 3.6 `GET /overview/risk-trend`

Query: global filters; `weeks` (int 1–26, default 13).

```json
{
  "points": [
    { "as_of_date": "2026-07-08", "run_id": 2, "critical": 9, "high": 41, "moderate": 188, "low": 4562, "margin_at_risk_usd": 19870.10 },
    { "as_of_date": "2026-09-30", "run_id": 14, "critical": 21, "high": 62, "moderate": 240, "low": 4477, "margin_at_risk_usd": 48213.55 }
  ]
}
```

Ascending by date; one point per distinct as-of date (latest succeeded run per date, `current` preferred). Source: `v_risk_trend`.

### 3.7 `GET /overview/store-comparison`

Query: `region_id*`, `category_id*` (store filter ignored here so all stores in scope are compared; the UI highlights selected stores).

```json
{
  "stores": [
    { "store_id": 3, "store_code": "S03", "store_name": "Tampa Westshore", "region_name": "Southeast",
      "positions": 400, "at_risk_positions": 19, "critical_positions": 7,
      "margin_at_risk_usd": 9811.20, "in_stock_rate": 0.9214 }
  ]
}
```

Sorted by `margin_at_risk_usd` desc. `in_stock_rate` trailing 28 days.

### 3.8 `GET /overview/category-heatmap`

Query: `region_id*`, `store_id*`, `category_id*`.

```json
{
  "stores": [ { "store_id": 3, "store_code": "S03" } ],
  "categories": [ { "category_id": 3, "category_name": "Electrical" } ],
  "cells": [
    { "store_id": 3, "category_id": 3, "positions": 60, "at_risk_positions": 8, "at_risk_rate": 0.1333, "margin_at_risk_usd": 6120.00 }
  ]
}
```

Dense: one cell for every (store, category) in scope.

### 3.9 `GET /overview/top-products`

Query: global filters; `limit` (1–50, default 8).

```json
{
  "items": [
    { "product_id": 118, "sku": "EL-10118", "product_name": "Voltrane 7,500-Watt Portable Generator", "category_name": "Electrical",
      "at_risk_stores": 3, "critical_stores": 2, "margin_at_risk_usd": 3120.44 }
  ]
}
```

Ordered by `margin_at_risk_usd` desc, then `at_risk_stores` desc. Includes only products with ≥ 1 at-risk store.

### 3.10 `GET /recommendations`

Query: global filters; `action_type*` (`expedite_po` | `reorder` | `monitor`; default all except `no_action`); `limit` (1–100, default 10).

```json
{
  "items": [
    {
      "priority_rank": 1, "store_id": 3, "store_code": "S03", "product_id": 118, "sku": "EL-10118",
      "product_name": "Voltrane 7,500-Watt Portable Generator", "category_name": "Electrical",
      "risk_tier": "critical", "stockout_probability": 0.9214, "margin_at_risk_usd": 1214.30,
      "action_type": "expedite_po", "urgency": "urgent",
      "recommended_order_units": 4, "recommended_order_cost_usd": 2596.00,
      "related_purchase_order": { "purchase_order_id": 104377, "po_number": "PO-104377" },
      "rationale": "PO-104377 is past its promised date (Sep 28); confirm the delivery date with Lakeshore Electric Distributors or request an expedite.",
      "days_until_projected_stockout": 1
    }
  ]
}
```

Ordered by `priority_rank` (global rank; when filters apply, the original global ranks are preserved — not re-numbered — and the UI displays the filtered order position).

### 3.11 `GET /risk/positions`

Query:

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `region_id*`, `store_id*`, `category_id*`, `supplier_id*` | int lists | — | |
| `risk_tier*` | enum list | all | |
| `action_type*` | enum list | all | |
| `below_reorder_point` | bool | — | `true` restricts to positions below ROP |
| `q` | string (1–64 chars) | — | SKU prefix (case-insensitive) OR product name substring (`ILIKE`) |
| `sort_by` | `priority` \| `product_name` \| `store_code` \| `category_name` \| `on_hand_units` \| `avg_daily_demand_units` \| `days_of_cover` \| `next_receipt_date` \| `stockout_probability` \| `risk_tier` \| `margin_at_risk_usd` | `priority` | `priority` = `priority_rank` asc nulls last, then tier desc, margin desc |
| `sort_dir` | `asc` \| `desc` | per column (`priority` asc; numeric desc) | |
| `page`, `page_size` | | 1, 50 | |

Response:

```json
{
  "items": [
    {
      "store_id": 3, "store_code": "S03", "store_name": "Tampa Westshore", "region_name": "Southeast",
      "product_id": 187, "sku": "PL-10187", "product_name": "Aquaveld 1/2 in. PEX-B Crimp Fitting Kit (25-Pack)",
      "category_id": 4, "category_name": "Plumbing", "supplier_id": 21, "supplier_name": "Gulfmark Plumbing Supply Co.",
      "on_hand_units": 100, "on_order_units": 0, "avg_daily_demand_units": 12.0, "days_of_cover": 8.3,
      "next_receipt_date": null, "next_receipt_units": null, "next_receipt_po_number": null, "next_receipt_overdue": false,
      "stockout_probability": 0.7568, "risk_tier": "critical", "margin_at_risk_usd": 148.88, "revenue_at_risk_usd": 391.88,
      "below_reorder_point": true, "action_type": "reorder", "urgency": "urgent", "priority_rank": 3,
      "recommended_order_units": 168
    }
  ],
  "page": 1, "page_size": 50, "total_items": 83, "total_pages": 2,
  "summary": {
    "positions": 83, "critical": 21, "high": 62, "moderate": 0, "low": 0,
    "margin_at_risk_usd": 43407.15
  }
}
```

`summary` aggregates the **filtered** set (all pages). Performance < 150 ms.

### 3.12 `GET /risk/positions/export.csv` (P1)

Same query params as 3.11 except pagination. Returns `text/csv; charset=utf-8` with `Content-Disposition: attachment; filename="stocksense_risk_positions_2026-09-30_run14.csv"`. First line: `# StockSense simulated dataset · run 14 · as of 2026-09-30 · values marked est_ are model estimates`. Header uses API field names; estimated columns prefixed `est_` (e.g., `est_stockout_probability`). > 10,000 rows → 400 `EXPORT_TOO_LARGE`.

### 3.13 `GET /positions/{store_id}/{product_id}`

Path IDs integers. 404 `STORE_NOT_FOUND` / `PRODUCT_NOT_FOUND` / `POSITION_NOT_FOUND` as applicable.

```json
{
  "run": { "run_id": 14, "as_of_date": "2026-09-30", "model_version": "stocksense-baseline-1.0" },
  "store": { "store_id": 3, "store_code": "S03", "store_name": "Tampa Westshore", "region_name": "Southeast" },
  "product": { "product_id": 187, "sku": "PL-10187", "product_name": "Aquaveld 1/2 in. PEX-B Crimp Fitting Kit (25-Pack)",
               "category_name": "Plumbing", "brand_name": "Aquaveld", "unit_of_measure": "pack",
               "unit_price_usd": 24.98, "unit_cost_usd": 15.49 },
  "supplier": { "supplier_id": 21, "supplier_code": "SUP-021", "supplier_name": "Gulfmark Plumbing Supply Co.",
                "case_pack_qty": 12, "min_order_qty": 24 },
  "risk": {
    "risk_tier": "critical", "stockout_probability": 0.7568, "currently_out_of_stock": false,
    "binding_checkpoint_type": "window_end", "projected_stockout_date": "2026-10-09", "days_until_projected_stockout": 9,
    "drivers": [
      { "code": "coverage_gap", "label": "Coverage gap", "description": "Days of cover (8.3) are shorter than the time until replenishment (10.0 days)." },
      { "code": "no_inbound_supply", "label": "No inbound supply", "description": "Nothing is on order and inventory position is at or below the reorder point." },
      { "code": "supplier_unreliable", "label": "Supplier on-time below 80%", "description": "This lane's 90-day on-time rate is 70.4%." }
    ],
    "explanation": "On-hand inventory of 100 units covers about 8.3 days of forecast demand (12.0 units/day). No replenishment is on order; a new order from Gulfmark Plumbing Supply Co. typically arrives in 10.0 days (±2.0). This supplier delivered 70% of orders to this store on time over the last 90 days. Estimated stockout probability before replenishment: 75.7% (Critical). Estimated gross margin at risk: $149 (model estimate)."
  },
  "inventory": {
    "on_hand_units": 100, "on_order_units": 0, "inventory_position_units": 100, "open_po_count": 0,
    "days_of_cover": 8.3, "next_receipt": null
  },
  "demand": {
    "forecast_method": "store_sku", "demand_pattern": "smooth",
    "base_daily_demand_units": 12.0, "avg_daily_demand_units": 12.0, "daily_demand_std_units": 5.0,
    "observed_demand_cv": 0.4167, "demand_trend_ratio": 1.081,
    "lookback_days": 56, "clean_days": 49, "censored_days": 4, "promo_days": 3, "recent_censored_days": 2,
    "forecast_7d_units": 84.0, "forecast_14d_units": 168.0, "forecast_28d_units": 336.0,
    "forecast_7d_std_units": 13.23, "forecast_14d_std_units": 18.71, "forecast_28d_std_units": 26.46
  },
  "supply": {
    "lead_time_source": "lane", "n_received_pos": 27,
    "lead_time_mean_days": 10.0, "lead_time_std_days": 2.0,
    "mean_delay_days": 0.92, "on_time_rate": 0.7037, "protection_window_days": 10.0
  },
  "policy": {
    "service_level": 0.95, "review_period_days": 7, "distribution_family": "normal",
    "lead_time_demand_mean_units": 120.0, "lead_time_demand_std_units": 28.74,
    "safety_stock_units": 47.27, "reorder_point_units": 168, "order_up_to_units": 257, "below_reorder_point": true
  },
  "exposure": {
    "expected_shortage_units": 24.14, "lost_sale_rate": 0.65, "expected_lost_units": 15.69,
    "revenue_at_risk_usd": 391.88, "margin_at_risk_usd": 148.88
  },
  "checkpoints": [
    { "checkpoint_seq": 1, "checkpoint_type": "window_end", "purchase_order_id": null, "po_number": null, "arrival_date": null,
      "window_days": 10.0, "window_std_days": 2.0, "supply_units": 100,
      "demand_mean_units": 120.0, "demand_std_units": 28.74, "distribution_family": "normal",
      "stockout_probability": 0.7568, "expected_shortage_units": 24.14, "is_binding": true }
  ],
  "recommendation": {
    "action_type": "reorder", "urgency": "urgent", "priority_rank": 3,
    "recommended_order_units": 168, "recommended_order_cases": 14, "recommended_order_cost_usd": 2602.32,
    "related_purchase_order": null,
    "rationale": "Inventory position (100) is at or below the reorder point (168). Order 168 units (14 cases of 12) to reach the target stock position of 257."
  }
}
```

Driver `label`/`description` strings are produced by the backend (`explanations.describe_driver`) from stored values — the frontend does not compose them. Performance < 150 ms.

### 3.14 `GET /positions/{store_id}/{product_id}/history`

Query: `days` (int 7–180, default 56).

```json
{
  "days": [
    { "date": "2026-09-29", "units_sold": 11, "opening_on_hand_units": 122, "units_received": 0, "net_adjustment_units": 0,
      "closing_on_hand_units": 111, "availability_status": "in_stock", "is_censored": false,
      "promotion_id": null, "promotion_name": null }
  ],
  "forecast": [
    { "date": "2026-10-01", "horizon_day": 1, "forecast_units": 12.0, "promo_multiplier": 1.0 }
  ]
}
```

`days` ascending, covering `[as_of − days + 1, as_of]` from `mv_daily_position`. `forecast` = 28 days from `demand_forecast_daily` for the current run.

### 3.15 `GET /positions/{store_id}/{product_id}/projection`

Query: `history_days` (7–56, default 28), `horizon_days` (7–42, default 28).

```json
{
  "as_of_date": "2026-09-30",
  "reorder_point_units": 168, "safety_stock_units": 47.27,
  "projected_stockout_date": "2026-10-09",
  "points": [
    { "date": "2026-09-30", "kind": "actual", "on_hand_units": 100 },
    { "date": "2026-10-01", "kind": "projected", "expected_on_hand_units": 88.0, "band_low_units": 81.6, "band_high_units": 94.4,
      "forecast_units": 12.0, "receipts_units": 0 }
  ],
  "receipts": [
    { "date": "2026-10-07", "purchase_order_id": 104512, "po_number": "PO-104512", "units": 96, "overdue": false }
  ],
  "notes": "Expected inventory assumes forecast demand and expected PO arrival dates; the band is an approximate 80% range from demand uncertainty only."
}
```

(The `receipts` example shows the format; the hero position has none.) Computed by the service calling `analytics.leadtime.expected_arrival` and `analytics.risk.project_inventory` on stored inputs — identical to the pipeline. The projected stockout date must equal the stored snapshot value (API test).

### 3.16 `GET /positions/{store_id}/{product_id}/purchase-orders`

Query: `recent_received_limit` (0–20, default 5).

```json
{
  "open": [
    { "purchase_order_id": 104512, "po_number": "PO-104512", "order_date": "2026-09-27", "promised_delivery_date": "2026-10-06",
      "expected_arrival_date": "2026-10-07", "quantity_ordered": 96, "quantity_received": 0, "quantity_cancelled": 0,
      "open_quantity": 96, "status": "open", "overdue": false }
  ],
  "recent_received": [
    { "purchase_order_id": 103998, "po_number": "PO-103998", "order_date": "2026-09-13", "promised_delivery_date": "2026-09-22",
      "first_receipt_date": "2026-09-24", "quantity_ordered": 96, "quantity_received": 96, "quantity_cancelled": 0,
      "status": "received", "delay_days": 2 }
  ]
}
```

Status values: `open`, `partially_received`, `received`, `closed_short`; `overdue` boolean. Line-level for this product.

### 3.17 `GET /positions/{store_id}/{product_id}/sensitivity` (P1)

```json
{
  "baseline_probability": 0.7568,
  "scenarios": [
    { "key": "reliable_lead_times", "label": "Perfectly reliable lead times", "stockout_probability": 0.8970 },
    { "key": "pos_on_promised_date", "label": "Open POs arrive on promised date", "stockout_probability": 0.7568 },
    { "key": "poisson_variability", "label": "Demand variability at Poisson floor", "stockout_probability": 0.7758 },
    { "key": "no_promotion", "label": "No planned promotion", "stockout_probability": 0.7568 }
  ],
  "note": "One-at-a-time sensitivities; effects are not additive."
}
```

(Values computed for the hero example. Note that both variability counterfactuals *raise* the probability here: when expected demand (120) already exceeds supply (100), less uncertainty makes a shortfall more certain. The UI must render increases as well as decreases, and the caption must say so.)

### 3.18 `GET /suppliers/summary` (P1)

```json
{ "suppliers": 48, "flagged_suppliers": 5, "on_time_rate_90d": 0.8791, "mean_lead_time_days": 8.9, "overdue_open_pos": 37 }
```

### 3.19 `GET /suppliers` (P1)

Query: `region_id*`, `store_id*` (restrict PO stats to those stores), `category_id*`, `flagged_only` (bool), `sort_by` (`reliability_rank` | `on_time_rate` | `lead_time_cv` | `margin_at_risk_usd` | `at_risk_positions`), `sort_dir`.

```json
{
  "items": [
    { "supplier_id": 21, "supplier_code": "SUP-021", "supplier_name": "Gulfmark Plumbing Supply Co.", "category_name": "Plumbing",
      "pos_due_90d": 156, "on_time_rate": 0.6987, "in_full_rate": 0.9103,
      "mean_lead_time_days": 10.42, "std_lead_time_days": 2.61, "p90_lead_time_days": 14.0, "lead_time_cv": 0.2505,
      "overdue_open_pos": 4, "at_risk_positions": 14, "margin_at_risk_usd": 3410.92,
      "review_flag": true, "reliability_rank": 1 }
  ],
  "disclaimer": "Flags indicate association between supplier delivery performance and at-risk positions; they do not establish causation."
}
```

Not paginated (≤ 100 suppliers).

### 3.20 `GET /suppliers/{supplier_id}` (P1)

```json
{
  "supplier": { "supplier_id": 21, "supplier_code": "SUP-021", "supplier_name": "Gulfmark Plumbing Supply Co.", "category_name": "Plumbing" },
  "performance": { "on_time_rate": 0.6987, "in_full_rate": 0.9103, "mean_lead_time_days": 10.42, "std_lead_time_days": 2.61, "review_flag": true },
  "weekly_on_time": [ { "week_start_date": "2026-09-21", "pos_due": 6, "on_time_rate": 0.5 } ],
  "lead_time_histogram": [ { "lead_time_days": 9, "pos": 41 } ],
  "contract_lead_time_days_avg": 9.2,
  "lanes": [ { "store_id": 3, "store_code": "S03", "pos_received_180d": 27, "on_time_rate": 0.7037, "mean_lead_time_days": 10.0, "std_lead_time_days": 2.0, "overdue_open_pos": 1 } ],
  "exposed_positions": [ { "store_id": 3, "product_id": 187, "sku": "PL-10187", "product_name": "…", "risk_tier": "critical", "stockout_probability": 0.7568, "margin_at_risk_usd": 148.88 } ],
  "disclaimer": "…"
}
```

`weekly_on_time`: last 26 ISO weeks by promised date. `exposed_positions`: tier ≥ moderate, sorted by tier then margin, max 50.

### 3.21 `GET /forecasts/evaluation` (P1)

Query: `segment_type` (`overall` | `horizon_bucket` | `velocity_class` | `demand_pattern`, default `horizon_bucket`), `evaluation_basis` (optional filter).

```json
{
  "run_id": 14, "first_origin_date": "2026-07-15", "last_origin_date": "2026-09-02", "n_origins": 8,
  "rows": [
    { "model_name": "stocksense_v1", "evaluation_basis": "observed_in_stock", "segment_type": "horizon_bucket", "segment_value": "1-7",
      "n_observations": 251004, "mae": null, "wape": null, "bias_rate": null }
  ],
  "notes": {
    "observed_in_stock": "Compares forecasts with observed sales on days the item was in stock. Stockout days are excluded because true demand is unknown.",
    "simulated_latent": "Simulation-only check: compares forecasts with the simulator's hidden true demand, which a real retailer cannot observe."
  }
}
```

(Metric values intentionally shown as `null` in this spec — no accuracy is claimed before the backtest runs.)

### 3.22 `POST /scenarios/evaluate`

Request (all fields optional; omitted = neutral):

```json
{
  "scope": { "store_ids": null, "category_ids": null, "supplier_ids": [15] },
  "assumptions": {
    "lead_time_change_days": 4,
    "demand_change_rate": 0.20,
    "service_level": 0.95,
    "safety_stock_buffer_rate": 0.0
  }
}
```

Validation (Pydantic, 422 `VALIDATION_ERROR` on failure): `lead_time_change_days` int in [−7, 14]; `demand_change_rate` float in [−0.5, 1.0]; `service_level` float in [0.80, 0.995]; `safety_stock_buffer_rate` float in [−0.5, 1.0]; scope lists ≤ 100 IDs each, all must exist (422 `UNKNOWN_FILTER_VALUE`). Non-finite numbers rejected.

Response:

```json
{
  "run_id": 14, "as_of_date": "2026-09-30",
  "assumptions_applied": { "lead_time_change_days": 4, "demand_change_rate": 0.2, "service_level": 0.95, "safety_stock_buffer_rate": 0.0 },
  "positions_in_scope": 96,
  "baseline": {
    "positions_by_tier": { "critical": 6, "high": 9, "moderate": 14, "low": 67 },
    "at_risk_positions": 15, "mean_stockout_probability": 0.0912, "expected_shortage_units": 210.4,
    "revenue_at_risk_usd": 22011.30, "margin_at_risk_usd": 8102.50,
    "lead_time_demand_units": 5120.0, "safety_stock_units": 1880.2, "safety_stock_value_usd": 61022.00,
    "positions_below_reorder_point": 22, "recommended_order_units": 1404, "recommended_order_value_usd": 38110.00,
    "annual_carrying_cost_usd": 15255.50, "annual_expected_shortfall_margin_usd": 9310.00, "avg_lead_time_days": 9.1
  },
  "scenario": { "…": "same fields" },
  "delta": {
    "absolute": { "at_risk_positions": 19, "margin_at_risk_usd": 9801.20, "…": 0 },
    "relative": { "at_risk_positions": 1.2667, "margin_at_risk_usd": 1.2097, "…": null }
  },
  "tier_transitions": {
    "order": ["critical", "high", "moderate", "low"],
    "matrix": [[6, 0, 0, 0], [8, 1, 0, 0], [5, 6, 3, 0], [2, 5, 12, 48]]
  },
  "by_category": [
    { "category_id": 3, "category_name": "Electrical", "baseline_margin_at_risk_usd": 8102.50, "scenario_margin_at_risk_usd": 17903.70,
      "baseline_at_risk_positions": 15, "scenario_at_risk_positions": 34 }
  ],
  "top_changes": [
    { "store_id": 3, "product_id": 118, "sku": "EL-10118", "product_name": "Voltrane 7,500-Watt Portable Generator", "store_code": "S03",
      "baseline_tier": "high", "scenario_tier": "critical",
      "baseline_stockout_probability": 0.31, "scenario_stockout_probability": 0.88,
      "baseline_margin_at_risk_usd": 480.10, "scenario_margin_at_risk_usd": 1911.42,
      "baseline_recommended_order_units": 2, "scenario_recommended_order_units": 6 }
  ],
  "warnings": [],
  "computation_ms": 312
}
```

- `matrix[i][j]` = positions with baseline tier `order[i]` and scenario tier `order[j]`.
- `relative` = `(scenario − baseline) / baseline`, `null` when baseline = 0. Rate metrics (`mean_stockout_probability`) report absolute difference only (relative `null`).
- `positions_in_scope = 0` → 200 with zeroed summaries and empty arrays.
- Nothing is persisted. Calculation source: 05 §10.

---

## 4. Backend structure for the API

| Module | Responsibility |
|--------|----------------|
| `api/app.py` | `create_app()`: CORS, request-ID middleware, timing log, error handlers, router registration under `/api/v1` |
| `api/deps.py` | `get_conn()` (SQLAlchemy connection per request, read-only transaction), `get_current_run()` (raises `ANALYTICS_NOT_READY`) |
| `api/errors.py` | `ApiError(code, status, message, details)`; handlers for `ApiError`, `RequestValidationError`, `HTTPException` (404 routes), generic `Exception` |
| `api/pagination.py` | `PageParams`, `Page[T]` generic response model |
| `api/routers/*.py` | One router per resource; thin: parse → service → response model |
| `api/schemas/*.py` | Pydantic models; shared enums (`RiskTier`, `ActionType`, …) defined once in `api/schemas/common.py` and mirrored from DB enums |
| `services/*.py` | Use cases; call repositories (`db/sql_loader`) and analytics functions; build response models |
| `api/export_openapi.py` | Writes `openapi.json` |

---

## 5. API test matrix (summary; full list in 10 §7)

| Area | Cases |
|------|-------|
| Valid requests | Every endpoint returns 200 with schema-valid body on the small preset |
| Invalid IDs | Unknown store/product/supplier path IDs → 404 with correct code; unknown filter IDs → 422 |
| Missing data | No current run → 503 `ANALYTICS_NOT_READY` on analytics endpoints; `/meta` returns `run: null` |
| Pagination | page/page_size bounds; beyond last page; totals equal `COUNT(*)` |
| Filters | Combinations of store × category × tier × action × search; summary equals SQL aggregate |
| Sorting | Each `sort_by` value; stable order |
| Scenario inputs | Neutral = stored baseline; boundaries accepted; out-of-range rejected; empty scope; unknown supplier |
| Consistency | Overview `at_risk_positions` = Risk Monitor `total_items` with tier filter critical+high; projection stockout date = detail `projected_stockout_date` |
| Server errors | Forced DB failure (monkeypatched engine) → 503 `DATABASE_UNAVAILABLE`; unexpected exception → 500 envelope without traceback |
