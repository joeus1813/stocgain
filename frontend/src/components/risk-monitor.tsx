"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ColumnDef } from "@tanstack/react-table";
import { useApi } from "@/lib/api/hooks";
import { apiBase, type Schema } from "@/lib/api/client";
import { apiFilters, useUrlState } from "@/lib/url-state";
import {
  formatCount as count,
  formatMoney as money,
  formatDate as date,
  formatDays as days,
  formatDecimal as decimal,
} from "@/lib/format";
import {
  Tier,
  Probability,
  Action,
  Loading,
  ErrorState,
  Empty,
} from "./shared/ui";
import { DataTable } from "./shared/data-table";
import { MultiSelect } from "./layout/filter-bar";
type Position = Schema<"RiskPosition">;
function Search({
  value,
  onSearch,
}: {
  value: string;
  onSearch: (v: string) => void;
}) {
  const [state, setState] = useState({ draft: value, source: value });
  if (state.source !== value) setState({ draft: value, source: value });
  const draft = state.draft;
  useEffect(() => {
    if (draft === value) return;
    const t = setTimeout(() => onSearch(draft), 300);
    return () => clearTimeout(t);
  }, [draft, value, onSearch]);
  return (
    <input
      aria-label="Search SKU or product"
      placeholder="Search SKU or product…"
      maxLength={64}
      value={draft}
      onChange={(e) => setState({ ...state, draft: e.target.value })}
    />
  );
}
export function RiskMonitor() {
  const { params, update } = useUrlState();
  const router = useRouter();
  const query = apiFilters(new URLSearchParams(params.toString()));
  const q = useApi<Schema<"RiskPositions">>(`/risk/positions?${query}`);
  const [exportError, setExportError] = useState("");
  const filters = useApi<Schema<"FiltersResponse">>("/filters");
  const tiers = (params.get("tier") ?? "").split(",").filter(Boolean);
  const detail = (p: Position) =>
    `/positions/${p.store_id}/${p.product_id}?return=${encodeURIComponent("/risk?" + params.toString())}`;
  const columns: ColumnDef<Position>[] = [
    {
      accessorKey: "product_name",
      header: "Product",
      cell: ({ row }) => (
        <div className="product-cell">
          <Link
            href={detail(row.original)}
            onClick={(e) => e.stopPropagation()}
            title={row.original.product_name}
          >
            {row.original.product_name}
          </Link>
          <small>{row.original.sku}</small>
        </div>
      ),
    },
    {
      accessorKey: "store_code",
      header: "Store",
      cell: ({ row }) => (
        <span title={row.original.store_name}>{row.original.store_code}</span>
      ),
    },
    { accessorKey: "category_name", header: "Category" },
    {
      accessorKey: "on_hand_units",
      header: "On hand",
      cell: ({ row }) => (
        <div className="number">{count(row.original.on_hand_units)}</div>
      ),
    },
    {
      accessorKey: "avg_daily_demand_units",
      header: "Est. / day",
      cell: ({ row }) => (
        <div className="number">
          {decimal(row.original.avg_daily_demand_units)}
        </div>
      ),
    },
    {
      accessorKey: "days_of_cover",
      header: "Cover",
      cell: ({ row }) => (
        <span
          title={
            row.original.days_of_cover === null ? "No recent demand" : undefined
          }
        >
          {days(row.original.days_of_cover)}
        </span>
      ),
    },
    {
      accessorKey: "next_receipt_date",
      header: "Next replenishment",
      cell: ({ row }) =>
        row.original.next_receipt_date ? (
          <>
            <span>{date(row.original.next_receipt_date)}</span>
            <small
              className={row.original.next_receipt_overdue ? "worse" : "muted"}
              style={{ display: "block" }}
            >
              {row.original.next_receipt_overdue ? "Overdue · " : ""}
              {row.original.next_receipt_po_number}
            </small>
          </>
        ) : (
          <span className="muted">None on order</span>
        ),
    },
    {
      accessorKey: "stockout_probability",
      header: "Est. probability",
      cell: ({ row }) => (
        <Probability
          value={row.original.stockout_probability}
          tier={row.original.risk_tier}
        />
      ),
    },
    {
      accessorKey: "risk_tier",
      header: "Risk tier",
      cell: ({ row }) => <Tier tier={row.original.risk_tier} />,
    },
    {
      accessorKey: "margin_at_risk_usd",
      header: "Est. GM at risk",
      cell: ({ row }) => (
        <div className="number">{money(row.original.margin_at_risk_usd)}</div>
      ),
    },
    {
      id: "priority",
      accessorFn: (p) => p.priority_rank,
      header: "Recommended action",
      cell: ({ row }) => (
        <Action
          action={row.original.action_type}
          units={row.original.recommended_order_units}
        />
      ),
    },
  ];
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">Position-level intelligence</div>
          <h1>Inventory Risk Monitor</h1>
          <p>
            {q.data
              ? `${count(q.data.total_items)} positions · ${count(q.data.summary.critical + q.data.summary.high)} at risk · ${count(q.data.summary.critical)} critical · ${money(q.data.summary.margin_at_risk_usd, true)} est. gross margin at risk`
              : "Search, compare, and prioritize your store–SKU positions."}
          </p>
        </div>
        <button
          disabled={!q.data || q.data.total_items > 10000}
          title={
            q.data && q.data.total_items > 10000
              ? "Narrow filters to at most 10,000 rows"
              : "Download all matching positions"
          }
          onClick={() =>
            void (async () => {
              try {
                const p = new URLSearchParams(query);
                p.delete("page");
                p.delete("page_size");
                const response = await fetch(
                  `${apiBase}/risk/positions/export.csv?${p}`,
                );
                if (!response.ok)
                  throw new Error("Export failed. Please try again.");
                const url = URL.createObjectURL(await response.blob());
                const a = document.createElement("a");
                a.href = url;
                a.download =
                  response.headers
                    .get("Content-Disposition")
                    ?.match(/filename="([^"]+)"/)?.[1] ??
                  "stocgain_risk_positions.csv";
                a.click();
                URL.revokeObjectURL(url);
                setExportError("");
              } catch (e) {
                setExportError(
                  e instanceof Error ? e.message : "Export failed",
                );
              }
            })()
          }
        >
          Export CSV ↓
        </button>
      </div>
      {exportError && <p role="alert">{exportError}</p>}
      <section className="card">
        <div className="risk-controls">
          <Search
            value={params.get("q") ?? ""}
            onSearch={(v) => update({ q: v })}
          />
          <div className="tier-controls" aria-label="Risk tiers">
            {["critical", "high", "moderate", "low"].map((t) => (
              <button
                key={t}
                aria-pressed={tiers.includes(t)}
                onClick={() =>
                  update({
                    tier: tiers.includes(t)
                      ? tiers.filter((x) => x !== t).join(",")
                      : [...tiers, t].join(","),
                  })
                }
              >
                <Tier tier={t} />
              </button>
            ))}
          </div>
          <select
            aria-label="Recommended action"
            value={params.get("action") ?? ""}
            onChange={(e) => update({ action: e.target.value })}
          >
            <option value="">All actions</option>
            <option value="expedite_po">Expedite PO</option>
            <option value="reorder">Reorder</option>
            <option value="monitor">Monitor</option>
            <option value="no_action">No action</option>
            <option value="expedite_po,reorder,monitor">
              Any recommended action
            </option>
          </select>
          <MultiSelect
            label="Suppliers"
            value={params.get("supplier") ?? ""}
            options={
              filters.data?.suppliers.map((s) => ({
                id: s.supplier_id,
                label: s.supplier_name,
              })) ?? []
            }
            onChange={(v) => update({ supplier: v })}
          />
          <label>
            <input
              type="checkbox"
              checked={params.get("below_rop") === "true"}
              onChange={(e) =>
                update({ below_rop: e.target.checked ? "true" : null })
              }
            />{" "}
            Below reorder point
          </label>
          <button
            className="text-button"
            onClick={() =>
              update({
                q: null,
                tier: null,
                action: null,
                supplier: null,
                below_rop: null,
                sort: null,
                dir: null,
              })
            }
          >
            Reset risk filters
          </button>
        </div>
        {q.isPending ? (
          <Loading label="Loading positions…" />
        ) : q.isError ? (
          <ErrorState error={q.error} retry={() => void q.refetch()} />
        ) : !q.data.items.length ? (
          <Empty
            title={
              params.get("q")
                ? `No SKU or product matches “${params.get("q")}”`
                : "No positions match these filters"
            }
          />
        ) : (
          <>
            <DataTable
              data={q.data.items}
              columns={columns}
              sort={{
                id: params.get("sort") ?? "priority",
                desc: params.get("dir") === "desc",
              }}
              onSort={(id) =>
                update({
                  sort: id,
                  dir:
                    params.get("sort") === id && params.get("dir") !== "desc"
                      ? "desc"
                      : "asc",
                })
              }
              onRow={(p) => router.push(detail(p))}
            />
            <div className="pagination">
              <span>
                Showing {count((q.data.page - 1) * q.data.page_size + 1)}–
                {count(
                  Math.min(q.data.page * q.data.page_size, q.data.total_items),
                )}{" "}
                of {count(q.data.total_items)}
              </span>
              <div>
                <label>
                  Rows{" "}
                  <select
                    aria-label="Rows per page"
                    value={params.get("page_size") ?? "50"}
                    onChange={(e) => update({ page_size: e.target.value })}
                  >
                    {[25, 50, 100, 200].map((n) => (
                      <option key={n}>{n}</option>
                    ))}
                  </select>
                </label>
                <button
                  disabled={q.data.page <= 1}
                  onClick={() => update({ page: String(q.data.page - 1) })}
                  aria-label="Previous page"
                >
                  ←
                </button>
                <span>
                  {q.data.page} / {q.data.total_pages}
                </span>
                <button
                  disabled={q.data.page >= q.data.total_pages}
                  onClick={() => update({ page: String(q.data.page + 1) })}
                  aria-label="Next page"
                >
                  →
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </>
  );
}
