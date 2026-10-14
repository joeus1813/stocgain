"use client";
import { useEffect, useState } from "react";
import { useApi } from "@/lib/api/hooks";
import type { Schema } from "@/lib/api/client";
import { useUrlState, globalQuery, globalKeys } from "@/lib/url-state";
export function MultiSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { id: number; label: string }[];
  onChange: (v: string) => void;
}) {
  const [search, setSearch] = useState("");
  const selected = value.split(",").filter(Boolean);
  return (
    <details className="select-menu">
      <summary>
        {label} <span>{selected.length ? selected.length : "All"}</span>⌄
      </summary>
      <div className="select-options">
        <input
          aria-label={`Search ${label}`}
          placeholder="Search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {options
          .filter((o) => o.label.toLowerCase().includes(search.toLowerCase()))
          .map((o) => (
            <label key={o.id}>
              <input
                type="checkbox"
                checked={selected.includes(String(o.id))}
                onChange={() =>
                  onChange(
                    selected.includes(String(o.id))
                      ? selected.filter((x) => x !== String(o.id)).join(",")
                      : [...selected, String(o.id)].join(","),
                  )
                }
              />
              {o.label}
            </label>
          ))}
        <button className="text-button" onClick={() => onChange("")}>
          Clear {label.toLowerCase()}
        </button>
      </div>
    </details>
  );
}
export function FilterBar() {
  const { params, update } = useUrlState();
  const [expanded, setExpanded] = useState(false);
  const filters = useApi<Schema<"FiltersResponse">>("/filters");
  const query = globalQuery(new URLSearchParams(params.toString()));
  useEffect(() => {
    try {
      if (query) localStorage.setItem("stocgain.filters.v1", query);
    } catch {}
  }, [query]);
  const f = filters.data;
  return (
    <div className={`filter-wrapper ${expanded ? "filters-open" : ""}`}>
      <button
        className="mobile-filter-toggle"
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
      >
        Filters {query ? "· Active" : ""} {expanded ? "−" : "+"}
      </button>
      <div className="filter-bar">
        <span className="eyebrow">Scope</span>
        <label className="region-select">
          <span className="sr-only">Region</span>
          <select
            aria-label="Region"
            value={params.get("region") ?? ""}
            onChange={(e) => update({ region: e.target.value, store: null })}
          >
            <option value="">All regions</option>
            {f?.regions.map((r) => (
              <option key={r.region_id} value={r.region_id}>
                {r.region_name}
              </option>
            ))}
          </select>
        </label>
        <MultiSelect
          label="Stores"
          value={params.get("store") ?? ""}
          options={
            f?.stores
              .filter(
                (s) =>
                  !params.get("region") ||
                  String(s.region_id) === params.get("region"),
              )
              .map((s) => ({
                id: s.store_id,
                label: `${s.store_code} · ${s.store_name}`,
              })) ?? []
          }
          onChange={(v) => update({ store: v })}
        />
        <MultiSelect
          label="Categories"
          value={params.get("category") ?? ""}
          options={
            f?.categories.map((c) => ({
              id: c.category_id,
              label: c.category_name,
            })) ?? []
          }
          onChange={(v) => update({ category: v })}
        />
        <button
          className="text-button"
          onClick={() => {
            try {
              localStorage.removeItem("stocgain.filters.v1");
            } catch {}
            update(Object.fromEntries(globalKeys.map((k) => [k, null])));
          }}
        >
          Reset filters
        </button>
        {filters.isError && (
          <span role="alert">
            Filter options unavailable{" "}
            <button onClick={() => void filters.refetch()}>Retry</button>
          </span>
        )}
      </div>
    </div>
  );
}
