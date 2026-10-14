"use client";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
export const globalKeys = ["region", "store", "category"] as const;
export function apiFilters(params: URLSearchParams): URLSearchParams {
  const api = new URLSearchParams();
  for (const [url, key] of Object.entries({
    region: "region_id",
    store: "store_id",
    category: "category_id",
    supplier: "supplier_id",
    tier: "risk_tier",
    action: "action_type",
  }))
    for (const v of (params.get(url) ?? "").split(",").filter(Boolean))
      api.append(key, v);
  for (const [url, key] of Object.entries({
    q: "q",
    below_rop: "below_reorder_point",
    sort: "sort_by",
    dir: "sort_dir",
    page: "page",
    page_size: "page_size",
  }))
    if (params.has(url)) api.set(key, params.get(url)!);
  return api;
}
export function useUrlState() {
  const params = useSearchParams();
  const router = useRouter();
  const path = usePathname();
  function update(values: Record<string, string | null>) {
    const next = new URLSearchParams(params.toString());
    next.delete("page");
    for (const [k, v] of Object.entries(values)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    if (globalKeys.some((key) => key in values)) {
      try {
        const scope = globalQuery(next);
        if (scope) localStorage.setItem("stocgain.filters.v1", scope);
        else localStorage.removeItem("stocgain.filters.v1");
      } catch {}
    }
    router.replace(`${path}?${next}`, { scroll: false });
  }
  return { params, update };
}
export function globalQuery(params: URLSearchParams): string {
  const next = new URLSearchParams();
  for (const k of globalKeys) if (params.get(k)) next.set(k, params.get(k)!);
  return next.toString();
}
