# 07 — UI/UX Specification

**Related:** `01_PRODUCT_REQUIREMENTS.md` (stories), `08_API_SPECIFICATION.md` (endpoints), `05_ANALYTICS_MODELS.md` (definitions)

---

## 1. Design principles

1. **Every element supports a decision.** Each widget below lists the decision it supports. If a widget can't name one, it doesn't ship.
2. **Answer first, detail on demand.** Pages lead with the conclusion (what's at risk, how much), then the "why", then the raw numbers.
3. **Color means something.** Neutral by default; color is reserved for risk state, deltas, and the single primary action color. No decorative color.
4. **Honest labeling.** Estimates are labeled; simulated data is labeled; definitions are one hover away.
5. **Dense but calm.** Analysts want information density; achieve it with alignment, tabular numerals, and whitespace rhythm, not with smaller fonts.
6. **No dead controls.** Every visible button, filter, and link works. Nothing pretends to place orders.

---

## 2. Visual direction

A light, restrained enterprise analytics product. Reference qualities (not to be copied): the clarity of modern financial dashboards, the quiet neutrality of developer tools, the data-forward tables of operations software.

| Do | Don't |
|----|-------|
| Light neutral canvas, white cards with hairline borders | Gradients, glassmorphism, neon accents |
| Dark navy ink for text and primary data | Pure black text or low-contrast gray text |
| Teal for interactive/primary; amber reserved for "estimate" and caution accents | Multicolored KPI cards |
| Risk tiers as small, consistent badges and meters | Big red banners, flashing indicators |
| Tabular numerals, right-aligned numbers | Center-aligned numeric columns |
| Thin, direct-labeled charts with clear axes | 3D, donut charts, chart junk, gratuitous animation |
| Purposeful empty states with a next step | Blank areas or generic "No data" |

Product mark: a simple wordmark "stocgain" in Inter Semibold with a small teal glyph (a stylized shelf with a downward-trending notch) drawn as an inline SVG. No resemblance to any retailer's branding (no orange, no aprons, no bullseye, no stars).

---

## 3. Design tokens

Implemented as CSS custom properties in `src/styles/globals.css` and exposed to Tailwind v4 via `@theme`. Names below are the binding token names.

### 3.1 Color — neutrals and brand

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-canvas` | `#F6F7F9` | App background |
| `--color-surface` | `#FFFFFF` | Cards, tables, sidebar |
| `--color-surface-muted` | `#F2F4F7` | Table header, hovered rows, input backgrounds |
| `--color-surface-sunken` | `#EAECF0` | Skeletons, progress tracks |
| `--color-border` | `#E4E7EC` | Card borders, dividers |
| `--color-border-strong` | `#D0D5DD` | Input borders, table outer border |
| `--color-ink-900` | `#0E1A2B` | Primary text, KPI values |
| `--color-ink-700` | `#344054` | Secondary text, table body |
| `--color-ink-500` | `#667085` | Labels, captions, axis text |
| `--color-ink-400` | `#98A2B3` | Placeholders, disabled |
| `--color-teal-50` | `#EEF8F7` | Active nav background, selected chip |
| `--color-teal-100` | `#D3EFEC` | Hover on teal-50 elements |
| `--color-teal-500` | `#14958A` | Chart primary series |
| `--color-teal-600` | `#0F7F76` | Primary buttons, links, focus ring base |
| `--color-teal-700` | `#0C665F` | Primary hover, active nav text |
| `--color-amber-50` | `#FFF8EB` | "Est." tag background, scenario-changed highlight |
| `--color-amber-500` | `#E08A0B` | Chart secondary series, caution icons |
| `--color-amber-700` | `#8F5405` | "Est." tag text |
| `--color-navy-700` | `#1F3A5F` | Chart baseline series, sidebar wordmark |

### 3.2 Color — semantic

| Token group | fg (text) | bg | border | solid (bars/meters) |
|-------------|-----------|----|--------|---------------------|
| `risk-critical` | `#B42318` | `#FEF3F2` | `#FECDCA` | `#D92D20` |
| `risk-high` | `#B54708` | `#FFF6ED` | `#F9DBAF` | `#EF6820` |
| `risk-moderate` | `#854A0E` | `#FEFBE8` | `#FEEE95` | `#EAAA08` |
| `risk-low` | `#475467` | `#F2F4F7` | `#E4E7EC` | `#98A2B3` |
| `delta-worse` | `#B42318` | `#FEF3F2` | — | — |
| `delta-better` | `#067647` | `#ECFDF3` | — | — |
| `info` | `#0C665F` | `#EEF8F7` | `#B8E2DE` | — |
| `error` | `#B42318` | `#FEF3F2` | `#FECDCA` | — |

"Worse/better" is semantic, not directional: an **increase** in margin at risk is `delta-worse`; an increase in in-stock rate is `delta-better`. Each metric declares its polarity in `lib/constants.ts`.

### 3.3 Color — charts

| Token | Hex | Role |
|-------|-----|------|
| `--chart-1` | `#0F7F76` | Primary series (teal) |
| `--chart-2` | `#1F3A5F` | Baseline / comparison series (navy) |
| `--chart-3` | `#E08A0B` | Scenario / highlight series (amber) |
| `--chart-4` | `#7A8BA8` | Tertiary series (slate blue) |
| `--chart-grid` | `#EAECF0` | Gridlines (horizontal only) |
| `--chart-axis` | `#667085` | Axis labels |
| `--chart-ref` | `#98A2B3` | Reference lines (reorder point, safety stock), dashed |
| Heatmap ramp (5 steps, at-risk share) | `#FFFFFF` → `#FEF0C7` → `#FDB022` → `#EF6820` → `#B42318` | Category × store heatmap |

Risk-tier colored charts use the `solid` values from §3.2. Never more than 4 categorical colors in one chart.

### 3.4 Typography

Fonts via `next/font/google`: **Inter** (variable) for UI; **JetBrains Mono** for SKUs, PO numbers, formulas. Numeric contexts (tables, KPIs, chart labels) apply `font-variant-numeric: tabular-nums`.

| Token | Size / line height | Weight | Usage |
|-------|--------------------|--------|-------|
| `text-page-title` | 28 / 35 | 600 | Page H1 |
| `text-section` | 18 / 27 | 600 | Card titles |
| `text-subsection` | 15 / 22.5 | 600 | Sub-headings inside cards |
| `text-body` | 15 / 22.5 | 400 | Default body |
| `text-table` | 13 / 20 | 400 | Table cells |
| `text-small` | 13 / 18 | 400 | Helper text, subtitles |
| `text-caption` | 12 / 16 | 500, uppercase, letter-spacing 0.04em | KPI labels, table headers |
| `text-kpi` | 28 / 34 | 600, tabular | KPI values |
| `text-kpi-sm` | 20 / 28 | 600, tabular | Secondary key numbers |
| `text-mono` | 12.5 / 18 | 500 | SKU, PO numbers |

Base font size 15px (owner-requested Stage 4 readability refinement). Minimum text size 12px.

### 3.5 Spacing, layout, radii, shadows, motion

| Token | Value |
|-------|-------|
| Spacing scale | 4, 8, 12, 16, 20, 24, 32, 40, 48, 64 px |
| Page gutter | 32 px (≥ 1024), 24 px (768–1023), 16 px (< 768) |
| Card padding | 20 px (≥ 768), 16 px (< 768) |
| Grid | 12 columns, 24 px gap (≥ 1280), 16 px gap below |
| Max content width | 1440 px (centered) |
| Sidebar width | 232 px expanded, 64 px collapsed rail |
| Top bar height | 64 px |
| `--radius-sm` | 6 px (inputs, chips) |
| `--radius-md` | 8 px (buttons, badges are full pill) |
| `--radius-lg` | 12 px (cards) |
| `--radius-xl` | 16 px (dialogs, sheets) |
| `--shadow-card` | `0 1px 2px rgba(16,24,40,0.05)` |
| `--shadow-raised` | `0 4px 12px rgba(16,24,40,0.08), 0 2px 4px rgba(16,24,40,0.04)` (popovers, tooltips) |
| `--ring-focus` | `0 0 0 3px rgba(15,127,118,0.28)` |
| Motion | 150 ms ease-out for hover/focus; 200 ms for drawers; no other animation; disabled under `prefers-reduced-motion` |
| Breakpoints | `sm` 640, `md` 768, `lg` 1024, `xl` 1280, `2xl` 1536 |
| Z-index | sidebar 30, top bar 40, popover 50, dialog 60, toast 70 |

### 3.6 Interaction states

| State | Treatment |
|-------|-----------|
| Hover (row, nav item) | `surface-muted` background |
| Hover (button primary) | `teal-700` |
| Focus visible | `--ring-focus`, never removed |
| Active nav | `teal-50` background, `teal-700` text, 2 px teal left indicator |
| Selected chip | `teal-50` bg, `teal-700` text, `teal-600` border |
| Disabled | 50% opacity, `not-allowed` cursor, tooltip explaining why |
| Loading button | spinner icon, label unchanged, disabled |
| Changed-in-scenario value | `amber-50` background on the scenario cell |

### 3.7 Table style

- Header: `surface-muted`, `text-caption`, 40 px height, sticky.
- Rows: 44 px height (comfortable) — Risk Monitor allows "compact" 36 px toggle (P1).
- Numeric columns right-aligned, tabular; text left-aligned; badges centered in their column.
- Zebra striping: none. Row dividers: `border` color 1 px.
- First column sticky on horizontal scroll.
- Sortable headers show a chevron on hover; active sort shows filled chevron and `aria-sort`.

### 3.8 Chart style

- Horizontal gridlines only, `chart-grid`; no vertical gridlines; no chart borders.
- Axis labels 12 px `chart-axis`; y-axis on the left with compact formatting (`$12K`, `1.2K`).
- Direct labels preferred over legends when ≤ 3 series; legends top-left, inline, 12 px.
- Tooltips: white `--shadow-raised` card, title (date or category) in 12 px semibold, rows with color swatch, label, right-aligned value with units; estimates prefixed "Est.".
- Lines 2 px; bars with 4 px top radius; area fills at 12% opacity.
- Every chart has a title, a one-line subtitle stating the measure and window, and an `aria-label` summary.

---

## 4. Content, labeling, and formatting

### 4.1 Simulated dataset badge

- Top bar, right side, on every page: pill with `info` colors: icon `FlaskConical` + text **"Simulated Retail Dataset"**. Clicking opens a popover: provenance statement (06 §1.2, populated from `/meta`), preset, seed, date range, link "Read the methodology →".
- Footer line on Methodology page repeats the statement.
- Mobile: badge collapses to the icon with an accessible label; the popover still works.

### 4.2 Estimate labeling

- Any model-derived value (forecasts, probabilities, exposure, projections, safety stock, reorder points) shows either an "Est." tag (`amber-50`/`amber-700`, 11 px, pill) next to its label or "(model estimate)" in text.
- Observed values (on hand, units sold, PO quantities, on-time rate) have no tag.
- Scenario values carry a "Scenario" tag.

### 4.3 Definitions and tooltips

Every KPI and column header has an info tooltip (`Info` icon, 14 px) with: **definition**, **time window**, **source** (e.g., "Calculated from purchase orders and receipts"). Tooltip text lives in `lib/definitions.ts`, a single dictionary keyed by API field name, reused by KPI cards, table headers, and the Methodology page.

### 4.4 Terminology (use exactly)

| Use | Not |
|-----|-----|
| Position (store-SKU) | Item, record |
| Stockout probability | Risk score, risk % |
| Est. gross margin at risk | Lost profit, lost revenue |
| Days of cover | Days of supply (unless defined) |
| Next replenishment | Next delivery (when no PO exists) |
| Reorder point / Target stock (order-up-to) | Min / Max |
| Inventory position | Total inventory |
| Recommended action | Task, order |

### 4.5 Status components

- **RiskTierBadge**: pill, 22 px height, tier `bg`/`fg`/`border`, label "Critical/High/Moderate/Low", leading 6 px dot in `solid`.
- **ProbabilityMeter**: 64 × 6 px track (`surface-sunken`) with fill in the tier `solid` color proportional to probability, followed by the percentage text. Never color-only.
- **ActionChip**: neutral outline chip with icon: `expedite_po` → `Truck` "Expedite PO"; `reorder` → `PackagePlus` "Reorder 168"; `monitor` → `Eye` "Monitor"; `no_action` → em dash in `ink-400`.
- **Replenishment cell**: date + small text: "PO-104512", "Overdue · PO-104377" (critical fg), or "None on order" (`ink-500`).

### 4.6 Number and date formatting (`lib/format.ts`, binding)

| Kind | Rule | Examples |
|------|------|----------|
| Units (integers) | thousands separator, no decimals | `1,248` |
| Units per day | 1 decimal | `12.0` |
| Days | 1 decimal | `8.3 days`; `—` when NULL with tooltip "No recent demand" |
| Probability | percent, 1 decimal; `<0.1%` for 0 < p < 0.001; `>99.9%` for 0.999 < p < 1 | `75.7%` |
| Rates (on-time, in-stock) | percent, 1 decimal | `88.4%` |
| USD in tables, text, detail panels | whole dollars, separators | `$149`, `$2,602` |
| USD unit prices/costs | 2 decimals | `$24.98` |
| USD KPI totals | compact above $10,000 (1 decimal) | `$48.2K`, `$1.31M`; exact value in tooltip |
| Deltas | signed, same unit rules | `+131`, `−$3.4K`, `+4.2 pts` (percentage points for rate deltas) |
| Dates | `MMM D` in tables; `ddd, MMM D, YYYY` in headers | `Oct 9`; `Wed, Sep 30, 2026` |
| Timestamps | local time `MMM D, h:mm a` | `Oct 9, 3:05 PM` |

The backend's explanation text applies the identical rules (Python `explanations.py` implements the same formatter; a shared fixture test verifies both produce identical strings for 20 sample values).

---

## 5. App shell and navigation

```
┌──────────────┬────────────────────────────────────────────────────────────────────────────┐
│ ▣ stocgain │ Executive Overview                        [⚗ Simulated Retail Dataset]   │
│              │ As of Wed, Sep 30, 2026 · Analytics run #14                                 │
│ ◉ Overview   ├────────────────────────────────────────────────────────────────────────────┤
│ ○ Risk       │ [Region ▾] [Store ▾] [Category ▾]                         [Reset filters]   │
│   Monitor    │                                                                              │
│ ○ Suppliers  │                         page content                                         │
│ ○ Scenario   │                                                                              │
│   Lab        │                                                                              │
│ ─────────    │                                                                              │
│ ○ Method-    │                                                                              │
│   ology      │                                                                              │
│              │                                                                              │
│ v1.0 · Run 14│                                                                              │
└──────────────┴────────────────────────────────────────────────────────────────────────────┘
```

| Nav item | Route | Icon (lucide) | Priority |
|----------|-------|---------------|----------|
| Overview | `/` | `LayoutDashboard` | P0 |
| Risk Monitor | `/risk` | `ShieldAlert` | P0 |
| Suppliers | `/suppliers` | `Truck` | P1 (hidden until implemented — no dead links) |
| Scenario Lab | `/scenarios` | `SlidersHorizontal` | P0 |
| Methodology | `/methodology` | `BookOpen` | P0 (basic) |

Product Detail (`/positions/[storeId]/[productId]`) and Supplier Detail (`/suppliers/[supplierId]`) are reached by drill-down and show breadcrumbs.

**Global filter bar** (Overview, Risk Monitor, Suppliers): Region (single-select), Store (multi-select, options filtered by region), Category (multi-select). State lives in URL params `region`, `store`, `category` (comma-separated IDs). Sidebar links carry the current global params, so filters persist across pages. "Reset filters" clears them. The last-used global filters are also mirrored to `localStorage` (key `stocgain.filters.v1`, wrapped in try/catch) and restored only when a page is opened with no params.

Top bar shows the as-of date and run ID from `/meta` (so a viewer always knows what point in time the numbers describe).

---

## 6. Page 1 — Executive Overview (`/`)

**Primary objective:** In 30 seconds, understand how much inventory risk exists, where it concentrates, and what to do first.

### 6.1 Layout (≥ 1280 px)

```
┌ KPI ─────┬ KPI ─────┬ KPI ─────┬ KPI ─────┬ KPI ─────┬ KPI ─────┐
│ ACTIVE   │ AT-RISK  │ EST. GM  │ MEDIAN   │ SUPPLIER │ IN-STOCK │
│ POSITIONS│ POSITIONS│ AT RISK  │ DAYS OF  │ ON-TIME  │ RATE     │
│ 4,800    │ 83       │ $48.2K   │ COVER    │ 87.9%    │ 93.6%    │
│ 400 SKUs │ 1.7% ·21 │ Est.     │ 31.4 days│ 90 days  │ 28 days  │
│          │ crit +12▲│          │          │ 1,604 POs│ −0.8 pts │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
┌ Priority actions (8 cols) ────────────────────┬ Risk distribution (4) ─┐
│ # Product            Store  Tier  P    GM  Act│ ████████░░░░░░░░░░░░░░ │
│ 1 Voltrane 7,500W…   S03    Crit 92%  $1.2K ⚡│ Critical  21 · $31.0K  │
│ … 10 rows                     [View all →]    │ High      62 · $12.4K  │
│                                               │ Moderate 240 · $4.1K   │
│                                               │ Low    4,477 · $0.7K   │
├ Risk trend, 13 weeks (8 cols) ────────────────┼ Top at-risk products (4)┤
│ [Positions | Margin]  stacked area Crit/High  │ 1 Voltrane 7,500W… 3 st │
│                                               │ … 8 rows                │
├ Store comparison (5 cols) ──┬ Category × store heatmap (7 cols) ─────────┤
│ horizontal bars by store    │ rows: 8 categories, cols: 12 stores        │
└─────────────────────────────┴────────────────────────────────────────────┘
```

(Values in wireframes are placeholders for layout only.)

### 6.2 Components

| Component | Decision supported | Data (endpoint · fields) | Interactions |
|-----------|--------------------|--------------------------|--------------|
| **KPI: Active positions** | Context for all other numbers | `/overview/summary` · `active_positions`, `active_skus` | Tooltip definition |
| **KPI: At-risk positions** | Is today worse than last week? | `at_risk_positions`, `at_risk_rate`, `critical_positions`, `at_risk_positions_change` | Click → Risk Monitor filtered to Critical+High with current global filters |
| **KPI: Est. gross margin at risk** | How big is the problem in dollars? | `gross_margin_at_risk_usd`, `revenue_at_risk_usd` (subtitle) | Tooltip shows exact value, definition, "model estimate" note |
| **KPI: Median days of cover** | Is inventory generally lean or heavy? | `median_days_of_cover` | Tooltip explains median choice |
| **KPI: Supplier on-time rate** | Is supply reliable? | `supplier_on_time_rate`, `supplier_pos_due` | Click → Suppliers (P1; plain card in P0) |
| **KPI: In-stock rate** | Are shelves actually full? | `in_stock_rate`, `in_stock_rate_prior` (delta in pts) | Tooltip |
| **Priority actions** | What to do first | `/recommendations?limit=10` + global filters | Row click → Product Detail; "View all" → Risk Monitor sorted by priority with `action` ≠ no_action |
| **Risk distribution** | How is risk spread across tiers, by count and dollars? | `/overview/risk-distribution` · per tier `positions`, `margin_at_risk_usd` | Single 100% stacked horizontal bar (count share) + table of tiers with counts and $; clicking a tier → Risk Monitor filtered |
| **Risk trend** | Is risk improving or deteriorating? | `/overview/risk-trend` · 13 weekly points: `critical`, `high`, `margin_at_risk_usd` | Segmented control "Positions / Est. margin"; stacked area (Critical, High) for positions; single line for margin; tooltip lists both values; current week point emphasized |
| **Top at-risk products** | Which SKUs are a chain-wide problem? | `/overview/top-products?limit=8` · `product`, `at_risk_stores`, `margin_at_risk_usd` | Click → Risk Monitor filtered by search=SKU |
| **Store comparison** | Which stores need help? | `/overview/store-comparison` · per store `at_risk_positions`, `margin_at_risk_usd`, `in_stock_rate` | Horizontal bars of `margin_at_risk_usd` sorted desc, label shows at-risk count; selected-store bars highlighted when store filter active; click bar → sets store filter |
| **Category × store heatmap** | Where do category and location intersect? | `/overview/category-heatmap` · cells `at_risk_rate`, `at_risk_positions`, `margin_at_risk_usd` | Color = at-risk share (ramp §3.3), cell text = at-risk count; tooltip shows all three; click cell → Risk Monitor filtered by store + category; rows/cols respect global filters |

### 6.3 States

- Loading: KPI skeletons (label bar + value bar), chart skeletons sized to final layout (no layout shift).
- Empty (filters match nothing): replace grid with `EmptyState` "No positions match these filters" + "Reset filters".
- Error per widget: inline `ErrorState` inside the card with "Retry"; other widgets keep rendering.
- Analytics not ready: full-page `AnalyticsNotReady`.

### 6.4 Acceptance criteria

1. All 6 KPIs render values equal to the API response; API values equal the SQL in 04 §6.1 (tested at API level).
2. Changing any global filter refetches every widget and updates the URL.
3. Every KPI has a tooltip with definition, window, and source.
4. Clicking a heatmap cell opens Risk Monitor with matching filters, and the Risk Monitor's total count equals the cell's at-risk count when filtered to Critical+High.
5. Priority actions list order equals `priority_rank`.
6. No horizontal scroll at 1280 and 1440 px.

---

## 7. Page 2 — Inventory Risk Monitor (`/risk`)

**Primary objective:** Find, filter, and triage positions; drill into any one.

### 7.1 Layout

```
Inventory Risk Monitor
4,800 positions · 83 at risk (21 Critical, 62 High) · Est. GM at risk $48.2K   [⤓ Export CSV]
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ [🔍 Search SKU or product…] [Store ▾] [Category ▾] [Tier: ●Crit ●High ○Mod ○Low]         │
│ [Action ▾] [Supplier ▾ (P1)] [☐ Below reorder point only]                  [Reset]       │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Product              │Store│Category │On hand│Est/day│Cover │Next repl.   │Stockout│Tier │GM risk│Action        │
│ Voltrane 7,500W Gen… │ S03 │Electr.  │     2 │   1.9 │ 1.1d │Oct 6 ·PO-…  │▰▰▰ 92% │Crit │ $1,214│⚡Expedite PO  │
│ PL-10187 (mono)      │     │         │       │       │      │             │        │     │       │              │
│ …                                                                                                 │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Showing 1–50 of 83          Rows per page [50▾]      ‹ 1 2 ›        Filtered GM at risk $48.2K│
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Columns

| Column | Field(s) | Format | Sortable | Notes |
|--------|----------|--------|----------|-------|
| Product | `product_name`, `sku` | name (truncate 1 line, full in title) + mono SKU | yes (name) | Sticky |
| Store | `store_code`, `store_name` | code with name tooltip | yes | |
| Category | `category_name` | text | yes | |
| On hand | `on_hand_units` | units | yes | |
| Est. daily demand | `avg_daily_demand_units` | 1 decimal, Est. in header | yes | |
| Days of cover | `days_of_cover` | days | yes | `—` for NULL |
| Next replenishment | `next_receipt_date`, `next_receipt_po_number`, `next_receipt_overdue` | Replenishment cell (§4.5) | yes (date) | |
| Stockout probability | `stockout_probability` | ProbabilityMeter | yes | Est. in header |
| Risk tier | `risk_tier` | RiskTierBadge | yes (enum order) | |
| Est. GM at risk | `margin_at_risk_usd` | whole USD | yes | |
| Recommended action | `action_type`, `recommended_order_units` | ActionChip | yes (priority) | |

Default sort: `priority` (= `priority_rank` ascending, `no_action` last, then `risk_tier` desc, `margin_at_risk_usd` desc). URL params: `q`, `store`, `category`, `tier`, `action`, `supplier`, `below_rop`, `sort`, `dir`, `page`, `page_size`.

### 7.3 Interactions

- Search: debounced 300 ms; matches SKU prefix or product name substring (case-insensitive) server-side.
- Filters: multi-select popovers with checkboxes and counts not required (avoid extra queries).
- Tier chips toggle; default from URL; if no `tier` param, all tiers shown.
- Row click or Enter on focused row → Product Detail; Back returns with identical URL (state preserved).
- Export CSV (P1): downloads `stocgain_risk_positions_{as_of}_{run_id}.csv` via `/risk/positions/export.csv` with the current filters; button disabled with tooltip when > 10,000 rows (cannot happen at standard scale).
- Summary line updates from the response's `summary` object (counts by tier and Σ margin for the filtered set).

### 7.4 States and acceptance criteria

- Loading: table skeleton with 10 rows; keep filters interactive.
- Empty: "No positions match" + reset; if the only active filter is search, say "No SKU or product matches '{q}'".
- Error: inline error in table area with retry.
- AC1: Sorting by each sortable column produces the same order as the API (server-side).
- AC2: Filter combinations (store × category × tier × action × search) return consistent totals (API tests cover combinations).
- AC3: Pagination totals match `total_items`.
- AC4: CSV export rows equal the filtered table rows (all pages), with headers and a first-line comment `# stocgain simulated dataset · run {id} · as of {date}`.
- AC5: Back navigation from detail restores filters, sort, and page.

---

## 8. Page 3 — Product Risk Detail (`/positions/[storeId]/[productId]`)

**Primary objective:** Answer "Why is this product at risk, and what should we do?"

### 8.1 Layout

```
Risk Monitor / S03 Tampa Westshore / PL-10187
Aquaveld 1/2 in. PEX-B Crimp Fitting Kit (25-Pack)                         [Critical]
PL-10187 · Plumbing · Supplier: Gulfmark Plumbing Supply Co. · $24.98 / unit     [⧉ Copy summary]
┌ Why this is at risk (8) ───────────────────────────────┬ Key numbers (4) ──────────┐
│ On-hand inventory of 100 units covers about 8.3 days…  │ STOCKOUT PROBABILITY Est. │
│ [Coverage gap] [No inbound supply] [Supplier on-time]  │ 75.7%  ▰▰▰▰▰▰▰▱▱          │
│                                                        │ EST. GM AT RISK   $149    │
│ Recommended: Reorder 168 units (14 cases of 12),       │ DAYS OF COVER     8.3     │
│ ≈ $2,602 at cost · Urgent                              │ NEXT REPLENISHMENT        │
│ Rationale: Inventory position (100) is at or below…    │ none on order · ~10.0 d   │
├ Inventory projection (12) ─────────────────────────────┴───────────────────────────┤
│  units                                                                              │
│  200┤            ROP 168 - - - - - - - - - - - - - - - - - - - - - - - - - - - -    │
│     │ ███ actual on hand        ┆ today                                            │
│  100┤███████▇▆▅▅▄▃              ┆╲  expected (dashed) with 80% band                │
│   SS 47 - - - - - - - - - - - - ┆ -╲- - - - - - - - - - - - - - - - - - - - - -     │
│    0┼───────────────────────────┆───╲▁▁▁▁▁ projected stockout Oct 9 ▲ (shaded)      │
│      Sep 3                 Sep 30          Oct 14                Oct 28             │
├ Sales history, 56 days (7) ─────────────────────┬ Risk calculation (5) ─────────────┤
│ bars = units sold; hatched amber = censored days │ INVENTORY  On hand 100 · On order 0│
│ line = Est. demand level (forward 28 days)       │ DEMAND     12.0/day · σ 5.0 · …    │
│                                                  │ SUPPLY     Lead time 10.0 ± 2.0 …  │
│                                                  │ POLICY     SS 47.3 · ROP 168 · …   │
│                                                  │ RISK       Window 10.0 d · μ 120 … │
│                                                  │ EXPOSURE   Shortage 24.1 · …       │
│                                                  │ ▸ How the probability was computed │
├ Purchase orders (7) ────────────────────────────┼ Sensitivity (5, P1) ───────────────┤
│ PO#   Ordered Promised Expected Open  Status     │ If lead times were perfectly       │
│ …                                                │ reliable: 89.7% (vs 75.7%) …       │
└──────────────────────────────────────────────────┴────────────────────────────────────┘
```

### 8.2 Components

| Component | Decision supported | Data | Details |
|-----------|--------------------|------|---------|
| Header | Identity | `/positions/{s}/{p}` · identity block | Tier badge; "Copy summary" copies explanation + recommendation text to clipboard (toast "Copied") |
| **Why this is at risk** | Understand the cause | `explanation`, `risk_drivers`, `recommendation` | Explanation paragraph (text-body, max 70ch); driver chips with tooltips (definition per driver); recommendation callout (neutral surface, teal left border) showing action, quantity, cases, cost, urgency, rationale. **No order button.** |
| **Key numbers** | Severity at a glance | `stockout_probability`, `margin_at_risk_usd`, `days_of_cover`, next replenishment | Probability in `text-kpi` with meter; "Est." tags |
| **Inventory projection chart** | Will it run out, when, and does the PO save it? | `/positions/{s}/{p}/projection` | X: dates from as-of − 27 to as-of + 28. Series: actual closing on hand (solid navy step line, history); expected on hand (teal dashed, future); 80% band (teal 12% area); receipts as vertical markers with label "PO-104512 · +96" at ETA (amber); reference lines: reorder point (dashed `chart-ref`, labeled), safety stock (dotted, labeled); "Today" divider; projected stockout date marked with a small triangle and shaded region where expected on hand = 0. Tooltip: date, actual or expected units, band, receipts that day, forecast demand that day. Subtitle: "Expected inventory assumes forecast demand and expected PO arrival; band is approximate." |
| **Sales history chart** | Is the issue demand or supply? | `/positions/{s}/{p}/history?days=56` | Bars: daily units sold (navy); censored days rendered as amber hatched background column with a "Stockout day" legend; promo days marked with a small tag icon along the x-axis; a horizontal teal line for the Est. demand level extended 28 days into the future (from `f_t` daily values); tooltip: date, units sold, availability status in words, promo name |
| **Risk calculation (breakdown)** | Verify the math | `/positions/{s}/{p}` · breakdown groups; `checkpoints[]` | Six groups (Inventory, Demand, Supply, Policy, Risk, Exposure) of label/value rows with units and Est. tags; each row has a definition tooltip. Expandable "How the probability was computed" shows checkpoint table: type, window (days), supply, demand mean, demand sd, distribution, probability, binding marker; plus the formula in mono: `P(stockout) = 1 − Φ((S − μ)/σ)` (or "Negative binomial tail probability" for count families) |
| **Purchase orders** | Is inbound supply real and on time? | `/positions/{s}/{p}/purchase-orders` | Columns: PO number (mono), order date, promised date, expected arrival (Est.), ordered, received, open, status chip (Open / Partially received / Received / Closed short / Overdue). Shows open POs plus the last 5 received. Empty: "No open or recent purchase orders." |
| **Sensitivity** (P1) | Which inputs drive this risk, and in which direction? | `/positions/{s}/{p}/sensitivity` | Rows of counterfactuals with "would be X% (vs Y%)" and a small horizontal bar of the change; caption "One-at-a-time sensitivities; effects are not additive." |
| Lead-time mini-panel (P1) | Is the supplier the problem? | `/positions/{s}/{p}` · `lane` | Lane on-time rate, mean ± sd lead time, source (lane/supplier/contract), number of POs used |

### 8.3 States and acceptance criteria

- Unknown store/product → 404 page with "Back to Risk Monitor".
- Loading: skeletons per card.
- AC1: Every number in the explanation equals the corresponding breakdown value (same formatting) — Playwright test on the hero-like top position.
- AC2: Projection chart's projected stockout marker date equals `projected_stockout_date`.
- AC3: Censored days in the history chart equal `mv_daily_position.is_censored` for those dates.
- AC4: Recommendation callout shows quantity only when `recommended_order_units` is non-null.
- AC5: The page renders a coherent view for each of: critical with PO, critical without PO, low risk, zero-demand, chain-fallback positions (fixtures chosen from the small preset in E2E).

---

## 9. Page 4 — Supplier Performance (`/suppliers`, P1)

**Primary objective:** Identify suppliers whose delivery behavior is associated with inventory risk.

### 9.1 Layout

```
Supplier Performance                                   (global filters: Region/Store/Category)
┌ KPI: Suppliers flagged ┬ KPI: On-time (90d) ┬ KPI: Mean lead time ┬ KPI: Overdue open POs ┐
├ Reliability vs. variability (scatter, 6) ─────────┬ Ranked suppliers (6) ─────────────────┤
│ x: on-time rate (90d)  y: lead-time CV            │ Rank Supplier  On-time In-full LT±sd  │
│ point size: est. GM at risk; flagged = outlined   │ Overdue  At-risk  GM risk  [Review]   │
└───────────────────────────────────────────────────┴───────────────────────────────────────┘
Note: Flags show association between delivery performance and at-risk positions, not causation.
```

### 9.2 Components

| Component | Decision | Data | Interactions |
|-----------|----------|------|--------------|
| KPIs | Scale of supply issues | `/suppliers/summary` | Tooltips |
| Scatter | Which suppliers are both late and inconsistent? | `/suppliers` items: `on_time_rate`, `lead_time_cv`, `margin_at_risk_usd`, `review_flag` | Quadrant guides at on-time 0.80 and CV 0.35 (dashed); hover tooltip; click point → supplier detail |
| Ranked table | Order of supplier conversations | `/suppliers` | Columns listed in 01 US-30; default sort on-time ascending; click row → detail |
| Supplier detail (`/suppliers/[id]`) | Diagnose one supplier | `/suppliers/{id}` | Weekly on-time rate (bars, 26 weeks) with PO counts in tooltip; lead-time histogram (1-day bins) with contract lead time reference line; lanes table by store (POs, on-time, mean ± sd LT, overdue); exposed positions table (current run positions with this primary supplier and tier ≥ moderate) linking to detail |

Acceptance: values equal `v_supplier_performance`; disclaimer visible; flagged suppliers listed first when sorted by flag.

---

## 10. Page 5 — Scenario Lab (`/scenarios`)

**Primary objective:** Show how risk, recommendations, and inventory investment change under different operating assumptions — live, credibly, and clearly.

### 10.1 Layout

```
Scenario Lab                                                         [⚗ Simulated Retail Dataset]
Recalculates stockout risk and replenishment using the same model as the dashboard.
┌ Assumptions (4, sticky) ─────────┬ Results (8) ────────────────────────────────────────────────┐
│ SCOPE                            │ "At-risk positions rise from 83 to 214 (+131); estimated     │
│ Stores     [All ▾]               │  gross margin at risk rises from $48.2K to $131.9K."         │
│ Categories [All ▾]               │ ┌ Comparison ───────────────────────────────────────────────┐ │
│ Suppliers  [SUP-015 ×]           │ │ Metric                   Baseline  Scenario   Δ     Δ%    │ │
│ 412 positions in scope           │ │ NEAR-TERM RISK                                            │ │
│                                  │ │ At-risk positions             83       214  +131  +158%   │ │
│ ASSUMPTIONS                      │ │ Critical positions            21        97   +76  +362%   │ │
│ Supplier lead time   [+4 days]   │ │ Mean stockout probability   6.1%     14.8%  +8.7 pts      │ │
│ ─────────●──────────  −7 … +14   │ │ Est. GM at risk          $48.2K   $131.9K +$83.7K +174%   │ │
│ Demand               [+20%]      │ │ REPLENISHMENT POLICY                                      │ │
│ ───────●────────────  −50…+100%  │ │ Positions below ROP          402       771   +369         │ │
│ Service level        [95.0%]     │ │ Recommended order value   $310K     $598K   …             │ │
│ ──────────────●─────  80…99.5%   │ │ Safety stock value        $1.21M    $1.58M  …             │ │
│ Safety stock buffer  [0%]        │ │ TRADEOFF (annualized, assumptions)                        │ │
│ ────●───────────────  −50…+100%  │ │ Carrying cost of SS       $302K     $395K   …             │ │
│                                  │ │ Expected shortfall margin $96K      $201K   …             │ │
│ PRESETS                          │ └───────────────────────────────────────────────────────────┘ │
│ [Supplier disruption] [Demand    │ ┌ Tier transitions ───────┐┌ Margin at risk by category ────┐ │
│  surge] [Higher service] [Lean]  │ │ 4×4 matrix              ││ grouped bars base vs scenario  │ │
│                                  │ └─────────────────────────┘└────────────────────────────────┘ │
│ [↺ Reset to baseline]            │ ┌ Largest changes (20) ─────────────────────────────────────┐ │
│ Updated 0.4 s ago · 312 ms       │ │ Product Store Tier→Tier  P base→scen  GM risk Δ  Order Δ  │ │
│                                  │ └───────────────────────────────────────────────────────────┘ │
│                                  │ How to read this · Warnings                                   │
└──────────────────────────────────┴───────────────────────────────────────────────────────────────┘
```

(All values are layout placeholders.)

### 10.2 Controls

| Control | Type | Range / step | Default | Display |
|---------|------|--------------|---------|---------|
| Stores / Categories / Suppliers | multi-select comboboxes with search | valid IDs | all | chips; "N positions in scope" updates from the response |
| Supplier lead time change | slider + numeric stepper | −7 … +14 days, step 1 | 0 | "+4 days" |
| Demand change | slider + numeric input | −50% … +100%, step 5 | 0 | "+20%" |
| Service level | slider + numeric input | 80.0% … 99.5%, step 0.5 | from `/meta` (95.0%) | "95.0%" with helper "z = 1.645" |
| Safety stock buffer | slider + numeric input | −50% … +100%, step 5 | 0 | "+0%" |
| Presets (P1) | buttons | — | — | Supplier disruption (+4 d, +20%); Demand surge (+30%); Higher service (98%); Lean inventory (90%, −20% buffer) — presets set controls only; scope unchanged |
| Reset to baseline | button | — | — | Restores defaults and empty scope |

Behavior:

- Evaluation is automatic: any change triggers `POST /scenarios/evaluate` after a 400 ms debounce. In-flight requests are cancelled (AbortController) when a newer one starts.
- While computing: results stay visible with a subtle "Recalculating…" indicator in the panel header (no full skeleton after first load).
- Numeric inputs validate locally against the same ranges as the API; invalid input shows an inline error and does not send a request.
- Scenario state is mirrored in the URL (`lt`, `dem`, `sl`, `buf`, `store`, `category`, `supplier`) so a scenario can be shared or reloaded.
- Changed controls show a small amber dot; "Reset to baseline" is disabled when everything is at defaults.

### 10.3 Results components

| Component | Content | Notes |
|-----------|---------|-------|
| Headline sentence | Generated client-side from `baseline`/`scenario` values: at-risk positions and margin at risk changes | Neutral wording; if no change: "No change from baseline." |
| Comparison grid | Metrics from 05 §10.3 grouped as Near-term risk / Replenishment policy / Tradeoff | Δ colored by polarity; Δ% shown only when baseline ≠ 0; tradeoff rows labeled "annualized, uses 25% carrying-cost assumption"; scenario cells changed from baseline get `amber-50` background |
| Tier transition matrix | 4×4 counts baseline tier (rows) → scenario tier (cols) | Diagonal neutral; above-diagonal (worse) cells tinted `risk-high.bg`, below (better) tinted `delta-better.bg`; zeros shown as `·` |
| Margin at risk by category | Grouped horizontal bars: baseline (navy) vs scenario (amber) per category | Sorted by scenario value |
| Largest changes table | 20 rows from `top_changes` | Columns: product + SKU, store, tier baseline → scenario (two badges with arrow), P baseline → scenario, Δ GM at risk, recommended order baseline → scenario; row click → Product Detail (detail shows baseline values; a note explains the detail page is not scenario-adjusted) |
| How to read this | Static text from 05 §10.4 | Always visible, collapsed by default |
| Warnings | `warnings[]` from API | Amber info boxes |

### 10.4 States and acceptance criteria

- First load: baseline evaluation (neutral) shown immediately (request on mount).
- Error: error box in results with "Retry"; controls stay usable.
- Scope with zero positions: API returns 200 with `positions_in_scope = 0`; UI shows empty state "No positions in this scope."
- AC1: Neutral assumptions show Δ = 0 for every metric and match Overview totals for the same scope (at-risk count, margin at risk).
- AC2: Lead time +4 days and demand +20% increases at-risk positions and margin at risk (aggregate) on the standard dataset.
- AC3: Raising service level increases safety stock value and lowers annual expected shortfall margin, and leaves near-term risk metrics unchanged.
- AC4: Reset restores defaults and baseline results.
- AC5: p95 end-to-end update < 1.5 s on standard dataset (measured in E2E with timing log).
- AC6: Invalid input (e.g., typing 30 days) is blocked client-side; API 422 is still handled if bypassed.

---

## 11. Page 6 — Analytics Methodology (`/methodology`)

**Primary objective:** Make the product credible: show exactly where data comes from and how every number is computed.

Layout: left sticky table of contents (desktop), content column max 760 px, readable typography (16 px body for this page).

| Section | Content | Live data |
|---------|---------|-----------|
| 1. Data provenance | Provenance statement; preset, seed, date range, generator version, row counts | `/meta` |
| 2. The simulated retailer | Network (12 stores, 4 regions, 400 SKUs, 48 suppliers); how demand is simulated; the naive legacy policy and why it causes censored-demand stockouts; demo events E1–E5 | `/meta` (counts, events list) |
| 3. Demand forecasting | Clean vs censored days; EWMA; weekday index; promotions; fallbacks; an **illustrative** censoring diagram based on worked example 4 (labeled "Illustrative example — not from the dataset") | — |
| 4. Forecast evaluation (P1) | Table: model × basis × horizon bucket (MAE, WAPE, bias); explanation of bases; simulation-only label | `/forecasts/evaluation` |
| 5. Stockout risk | Protection window, checkpoints, the formula, distributions for slow movers, tiers | `/meta` thresholds |
| 6. Safety stock and reorder point | Formulas; service level table (z values) | `/meta` service level |
| 7. Financial exposure | Formula; lost-sale rates table; what it isn't | `/meta` lost-sale rates |
| 8. Recommendations | Rule table; prioritization order; "decision support only" | — |
| 9. Scenario Lab | What each lever changes | — |
| 10. Assumptions & limitations | 05 §16 list | — |
| 11. Technical architecture | Simple diagram (static SVG): PostgreSQL → SQL views → Python analytics → FastAPI → Next.js | `/meta` run id, model version |

Formulas are shown in styled mono blocks (no math-rendering dependency). Acceptance: every parameter value on the page comes from `/meta`; no hardcoded thresholds in page copy.

---

## 12. Shared component specifications

| Component | Props (TypeScript sketch) | Behavior |
|-----------|---------------------------|----------|
| `AppShell` | `children` | Sidebar + top bar + content; collapsible sidebar state in localStorage |
| `TopBar` | `title`, `subtitle?` | As-of and run from `useMeta()`; `DatasetBadge` |
| `FilterBar` | `scope: 'global'` | Reads/writes URL params; options from `/filters` |
| `KpiCard` | `label`, `value`, `format`, `subtitle?`, `delta?: {value, polarity, unit}`, `estimate?: boolean`, `definitionKey`, `href?` | Skeleton when loading; delta chip colored by polarity |
| `RiskTierBadge` | `tier` | §4.5 |
| `ProbabilityMeter` | `value`, `tier` | §4.5 |
| `ActionChip` | `action`, `units?` | §4.5 |
| `DataTable<T>` | `columns`, `data`, `sort`, `onSortChange`, `pagination`, `onRowClick`, `loading`, `emptyState` | TanStack Table in manual (server) mode; keyboard row navigation |
| `ChartCard` | `title`, `subtitle`, `children`, `ariaLabel`, `actions?` | Consistent card chrome |
| `ExplanationCard` | `text`, `drivers`, `recommendation` | |
| `RiskBreakdown` | `groups`, `checkpoints` | Collapsible checkpoint table |
| `AssumptionControl` | `label`, `min`, `max`, `step`, `value`, `format`, `onChange` | Slider + numeric input, synced; validation message |
| `ComparisonGrid` | `baseline`, `scenario`, `delta`, `metrics` | Polarity-aware coloring |
| `TierTransitionMatrix` | `matrix` | |
| `EmptyState` | `icon`, `title`, `description`, `action?` | |
| `ErrorState` | `error: ApiError`, `onRetry` | Shows message and code in small mono |
| `AnalyticsNotReady` | — | Explains and shows `make analytics` / `make pipeline` |
| `LoadingSkeleton` | `variant` | Shaped like final content |

---

## 13. Chart inventory (what each chart measures)

| Chart | Page | Type | X | Y / encoding | Interaction |
|-------|------|------|---|--------------|-------------|
| Risk distribution | Overview | 100% stacked horizontal bar + tier table | share of positions | segments by tier (`solid` colors) | click segment/row → Risk Monitor |
| Risk trend | Overview | stacked area (positions) / line (margin) | as-of week (13 points) | Critical + High counts, or Σ margin at risk | toggle; tooltip |
| Store comparison | Overview | horizontal bar | Σ margin at risk | bars by store, label = at-risk count | click → store filter |
| Category heatmap | Overview | matrix | store | category rows; color = at-risk share; text = count | click → Risk Monitor |
| Inventory projection | Detail | step line + dashed line + band + markers | date (−27 … +28) | on hand units | tooltip |
| Sales history | Detail | bars + level line + censored background | date (−55 … 0, +28 for level) | units sold; Est. level | tooltip |
| Supplier scatter | Suppliers | scatter | on-time rate | lead-time CV; size = margin at risk | click → detail |
| On-time trend | Supplier detail | bars | ISO week (26) | on-time rate | tooltip with PO count |
| Lead-time histogram | Supplier detail | histogram | lead time (days) | PO count; contract LT reference | tooltip |
| Category margin comparison | Scenario Lab | grouped horizontal bars | margin at risk | baseline vs scenario by category | tooltip |

No pie or donut charts. No dual-axis charts.

---

## 14. Responsive behavior

| Width | Behavior |
|-------|----------|
| ≥ 1280 | Layouts as drawn; 6 KPIs in one row |
| 1024–1279 | KPIs 3 × 2; Overview rows stack to 2 columns where the drawn split is 8/4 → 7/5; heatmap scrolls horizontally if needed |
| 768–1023 | Sidebar collapses to a 64 px icon rail with tooltips; two-column card rows become single column; Scenario Lab assumptions panel becomes a top card (not sticky) |
| < 768 | Sidebar replaced by top app bar with menu button opening a sheet; KPIs 2 per row (1 per row < 400 px); tables scroll horizontally with sticky first column; charts keep a minimum height of 240 px; Scenario Lab controls in an accordion above results; filter bar becomes a "Filters" button opening a sheet |

Primary demo target: 1440 × 900 (MacBook), verified also at 1280 × 800. Mobile target: 390 × 844, "reasonably usable" (all content reachable, no overlapping elements, no horizontal page scroll; tables scroll inside their container).

---

## 15. Loading, empty, and error states (global rules)

- Skeletons mirror final layout dimensions; no spinners for page loads.
- Empty states always propose a next step (reset filters, change scope, run pipeline).
- Errors show a human message, the API error code in mono, and a Retry button; never raw stack traces.
- 404 routes: friendly page with links to Overview and Risk Monitor.
- Network offline: TanStack Query error state; retry with exponential backoff (max 2 retries).

---

## 16. Accessibility

- WCAG 2.1 AA color contrast for text (all `fg` on `bg` pairs above meet ≥ 4.5:1; verify in Phase 8 with an automated check such as axe in Playwright).
- Tier and status never conveyed by color alone (text labels always present).
- All interactive elements keyboard-reachable; visible focus ring; logical tab order; skip-to-content link.
- Charts: `role="img"` with `aria-label` summarizing the key insight; main charts (risk trend, projection) offer a "View data" toggle rendering an accessible table (P1).
- Sliders use Radix Slider (ARIA compliant) paired with numeric inputs.
- Tooltips accessible via focus, not hover only.

---

## 17. Key user flows

```mermaid
flowchart LR
    O[Overview] -->|KPI / heatmap / tier click| RM[Risk Monitor<br/>pre-filtered]
    O -->|Priority action row| PD[Product Detail]
    RM -->|row click| PD
    PD -->|breadcrumb / back| RM
    O -->|Scenario Lab nav| SL[Scenario Lab]
    SL -->|Largest changes row| PD
    O -->|Supplier KPI (P1)| SP[Suppliers]
    SP -->|row / point| SD[Supplier Detail]
    SD -->|exposed position| PD
    any[Any page] -->|Dataset badge| ME[Methodology]
```

---

## 18. Page → endpoint matrix

| Page | Endpoints |
|------|-----------|
| Shell (all pages) | `GET /meta`, `GET /filters` |
| Overview | `GET /overview/summary`, `GET /overview/risk-distribution`, `GET /overview/risk-trend`, `GET /overview/store-comparison`, `GET /overview/category-heatmap`, `GET /overview/top-products`, `GET /recommendations` |
| Risk Monitor | `GET /risk/positions`, `GET /risk/positions/export.csv` (P1) |
| Product Detail | `GET /positions/{store_id}/{product_id}`, `GET /positions/{store_id}/{product_id}/history`, `GET /positions/{store_id}/{product_id}/projection`, `GET /positions/{store_id}/{product_id}/purchase-orders`, `GET /positions/{store_id}/{product_id}/sensitivity` (P1) |
| Suppliers (P1) | `GET /suppliers/summary`, `GET /suppliers`, `GET /suppliers/{supplier_id}` |
| Scenario Lab | `POST /scenarios/evaluate`, `GET /meta` |
| Methodology | `GET /meta`, `GET /forecasts/evaluation` (P1) |
