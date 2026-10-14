# Two-minute interview demo

Use the existing standard dataset and production frontend on http://localhost:3050. Open Overview and Scenario Lab once before the demo: a cold model replay can take about seven seconds. Keep `docs/screenshots/` available as an honestly labeled fallback. Do not reseed the database before presenting.

| Time | Action | Suggested narration |
|---|---|---|
| 0:00–0:20 | Overview: point to the dataset badge and six KPIs | “This is a fictional 12-store, 400-SKU retail network. PostgreSQL holds 180 days of internally reconciled sales, inventory, orders and receipts. Every dashboard metric comes from the actual API.” |
| 0:20–0:40 | Show heatmap, then open an at-risk cell | “SQL joins inventory with sales, derives rolling demand and supplier performance, and preserves historical cutoffs. This cell opens exactly the matching store/category positions.” |
| 0:40–1:05 | Open the first risk position; show explanation, projection and recommendation | “The model compares scheduled supply with uncertain demand before each receipt. These are estimated risks and suggested actions, not purchase orders. The explanation and breakdown expose the inputs.” Read the actual selected item's numbers; do not assume every item has an overdue PO. |
| 1:05–1:40 | Scenario Lab: Supplier disruption preset, then Higher service, then Reset | “Demand and supplier-delay changes rerun the same model. A higher service target changes safety stock and annual policy tradeoffs; it cannot change inventory already on the shelf. Reset reproduces baseline.” Wait for each result before describing it. |
| 1:40–2:00 | Methodology and forecast evaluation | “Observed WAPE is 57.66%, versus 58.39% for a 28-day naive baseline: only a 0.73-point improvement, and erratic-demand performance is worse. This project's strength is traceable SQL, reproducibility and transparent decisions—not a claim of commercial accuracy.” |

SQL code to have ready: `sql/views/020_mv_daily_position.sql`, the stockout episode view, and `sql/pipeline/extract_open_po_lines.sql`. Explain CTEs, window functions, integer receipt timing and `:as_of` boundaries. Never describe simulated estimates as realized business savings.

## Resume drafts (verified implementation only)

- Built a 26-table PostgreSQL retail simulation spanning 12 stores, 400 SKUs and 864,000 store-SKU-day records, with 15 analytical SQL queries and historical feature extraction.
- Developed a Python/FastAPI inventory-risk engine and six-screen Next.js analytics application with a real-data Scenario Lab; measured 1.383-second warm browser p95 over 20 full-scope evaluations on a local Apple Silicon machine.
- Evaluated censoring-aware forecasts against naive baselines using rolling-origin backtests on simulated data; observed WAPE was 57.66% versus 58.39% for a 28-day average.

Do not add unverified stockout-reduction, cost-saving, profitability, production-scale or deployment claims. Resume drafts should be shortened to fit the owner's actual role and independently explainable contribution.
