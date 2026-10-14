import { describe, it, expect } from "vitest";
import {
  formatCount,
  formatMoney,
  formatPrice,
  formatRate,
  formatProbability,
  formatDays,
  formatDate,
  formatDelta,
} from "@/lib/format";
describe("canonical presentation boundaries", () => {
  it.each([
    [0, "0.0%"],
    [0.00001, "<0.1%"],
    [0.001, "0.1%"],
    [0.7568, "75.7%"],
    [0.999, "99.9%"],
    [0.9999, ">99.9%"],
    [1, "100.0%"],
  ] as const)("probability %s", (value, expected) =>
    expect(formatProbability(value)).toBe(expected),
  );
  it("formats units, prices, totals, dates and signed changes", () => {
    expect(formatCount(1248)).toBe("1,248");
    expect(formatMoney(148.88)).toBe("$149");
    expect(formatMoney(48200, true)).toBe("$48.2K");
    expect(formatMoney(1310000, true)).toBe("$1.31M");
    expect(formatPrice(24.98)).toBe("$24.98");
    expect(formatRate(null)).toBe("—");
    expect(formatDays(null)).toBe("—");
    expect(formatDays(8.33)).toBe("8.3 days");
    expect(formatDate("2026-09-30", true)).toBe("Wed, Sep 30, 2026");
    expect(formatDelta(0.042, "rate")).toBe("+4.2 pts");
    expect(formatDelta(-34000, "money")).toBe("−$34.0K");
  });
});

import cases from "../fixtures/format_cases.json";
import { formatDecimal } from "@/lib/format";
const formatters: Record<string, (v: number | null) => string> = {
  count: (v) => formatCount(v!),
  decimal: formatDecimal,
  days: formatDays,
  rate: formatRate,
  probability: (v) => formatProbability(v!),
  money: (v) => formatMoney(v!),
  price: (v) => formatPrice(v!),
};
it.each(cases)("shared $kind $value → $expected", (c) =>
  expect(formatters[c.kind](c.value)).toBe(c.expected),
);
