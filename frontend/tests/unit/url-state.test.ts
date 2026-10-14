import { it, expect } from "vitest";
import { apiFilters, globalQuery } from "@/lib/url-state";
it("maps comma-separated URL filters to repeated bound API parameters", () => {
  const params = new URLSearchParams(
    "store=1,7&category=2&tier=critical,high&sort=priority&q=drill",
  );
  expect(apiFilters(params).getAll("store_id")).toEqual(["1", "7"]);
  expect(apiFilters(params).getAll("risk_tier")).toEqual(["critical", "high"]);
  expect(globalQuery(params)).toBe("store=1%2C7&category=2");
});
