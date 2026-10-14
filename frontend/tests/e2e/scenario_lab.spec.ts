import { test, expect } from "@playwright/test";
import { formatCount, formatMoney } from "../../src/lib/format";
test("neutral, disruption, policy tradeoff, reset and invalid inputs", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const overview = await (
    await request.get("http://localhost:8000/api/v1/overview/summary")
  ).json();
  await page.goto("/scenarios");
  await expect(
    page.getByRole("heading", { name: "Scenario comparison", exact: true }),
  ).toBeVisible({ timeout: 30000 });
  const metric = (key: string) => page.locator(`tr[data-metric="${key}"]`);
  await expect(metric("at_risk_positions").locator("td").nth(1)).toHaveText(
    formatCount(overview.at_risk_positions),
  );
  await expect(metric("margin_at_risk_usd").locator("td").nth(1)).toHaveText(
    formatMoney(overview.gross_margin_at_risk_usd, true),
  );
  await expect(metric("at_risk_positions").locator("td").nth(3)).toHaveText(
    "0",
  );
  const changed = page.waitForResponse(
    (r) =>
      r.url().endsWith("/scenarios/evaluate") &&
      r.request().postDataJSON().assumptions.lead_time_change_days === 4,
  );
  const started = Date.now();
  await page
    .getByRole("button", { name: "Supplier disruption", exact: true })
    .click();
  const result = await (await changed).json();
  expect(result.scenario.at_risk_positions).toBeGreaterThan(
    result.baseline.at_risk_positions,
  );
  expect(result.scenario.margin_at_risk_usd).toBeGreaterThan(
    result.baseline.margin_at_risk_usd,
  );
  await expect(metric("at_risk_positions").locator("td").nth(2)).toHaveText(
    formatCount(result.scenario.at_risk_positions),
  );
  console.log(
    `Scenario disruption end-to-end update: ${Date.now() - started} ms; server ${result.computation_ms} ms`,
  );
  const higher = page.waitForResponse(
    (r) =>
      r.url().endsWith("/scenarios/evaluate") &&
      r.request().postDataJSON().assumptions.service_level === 0.98,
  );
  await page
    .getByRole("button", { name: "Higher service", exact: true })
    .click();
  const high = await (await higher).json();
  expect(high.scenario.safety_stock_value_usd).toBeGreaterThan(
    high.baseline.safety_stock_value_usd,
  );
  expect(high.scenario.annual_expected_shortfall_margin_usd).toBeLessThan(
    high.baseline.annual_expected_shortfall_margin_usd,
  );
  expect(high.scenario.margin_at_risk_usd).toBe(
    high.baseline.margin_at_risk_usd,
  );
  await page
    .getByRole("button", { name: "Reset to baseline", exact: true })
    .click();
  await expect(
    page.getByLabel("Supplier lead time change", { exact: true }),
  ).toHaveValue("0");
  await expect(metric("at_risk_positions").locator("td").nth(3)).toHaveText(
    "0",
  );
  let requests = 0;
  page.on("request", (r) => {
    if (r.url().endsWith("/scenarios/evaluate")) requests++;
  });
  await page
    .getByLabel("Supplier lead time change", { exact: true })
    .fill("30");
  await expect(page.locator(".control-error")).toContainText(
    "between -7 and 14",
  );
  await page.waitForTimeout(700);
  expect(requests).toBe(0);
});
