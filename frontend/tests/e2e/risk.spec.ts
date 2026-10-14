import { test, expect } from "@playwright/test";
test("risk filters, server sorting, pagination, drilldown and back preserve state", async ({
  page,
  request,
}) => {
  await page.goto(
    "/risk?store=1&page_size=25&sort=margin_at_risk_usd&dir=desc",
  );
  await expect(page.locator("tbody tr")).toHaveCount(25);
  const api = await request.get(
    `${process.env.TEST_API_BASE_URL ?? "http://localhost:8000/api/v1"}/risk/positions?store_id=1&page_size=25&sort_by=margin_at_risk_usd&sort_dir=desc`,
  );
  const data = await api.json();
  await expect(page.locator("tbody tr").first()).toContainText(
    data.items[0].sku,
  );
  await page.getByRole("button", { name: "Next page", exact: true }).click();
  await expect(page).toHaveURL(/page=2/);
  await page.locator("tbody tr").first().getByRole("link").click();
  await expect(
    page.getByRole("heading", { name: "Inventory projection", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Purchase orders", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Risk Monitor", exact: true })
    .last()
    .click();
  await expect(page).toHaveURL(/page=2/);
  await page.getByLabel("Search SKU or product").fill("does-not-exist");
  await expect(page.getByText(/No SKU or product matches/)).toBeVisible();
  await expect(page.getByLabel("Search SKU or product")).toBeFocused();
  await page.getByRole("button", { name: "Reset risk filters" }).click();
  await expect(page.getByLabel("Search SKU or product")).toHaveValue("");
});
test("heatmap drills into exactly the at-risk cell count", async ({ page }) => {
  await page.goto("/");
  const cell = page.getByRole("button", { name: /Power Tools, S01:/ });
  await expect(cell).toBeVisible();
  const count = await cell.textContent();
  await cell.click();
  await expect(page).toHaveURL(/tier=critical%2Chigh/);
  await expect(page.locator(".page-heading p")).toContainText(
    `${count} positions`,
  );
});
