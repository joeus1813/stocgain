import { expect, test } from "@playwright/test";
import {
  formatCount,
  formatMoney,
  formatRate,
  formatDays,
} from "../../src/lib/format";

test("overview renders six real API metrics", async ({ page, request }) => {
  const response = await request.get(
    "http://localhost:8000/api/v1/overview/summary",
  );
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  await page.goto("/");
  const overview = page.getByRole("region", { name: "Inventory overview" });
  await expect(overview).toBeVisible();
  const expected = [
    formatCount(data.active_positions),
    formatCount(data.at_risk_positions),
    formatMoney(data.gross_margin_at_risk_usd, true),
    formatDays(data.median_days_of_cover),
    formatRate(data.supplier_on_time_rate),
    formatRate(data.in_stock_rate),
  ];
  await expect(overview.locator("dd")).toHaveText(expected);
  await expect(
    page.getByText("Simulated Retail Dataset", { exact: true }).first(),
  ).toBeVisible();
});
