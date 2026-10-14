import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("all primary pages and supplier detail have no serious or critical accessibility violations", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const positions = await (
    await request.get(
      `${process.env.TEST_API_BASE_URL ?? "http://localhost:8000/api/v1"}/risk/positions?page_size=1`,
    )
  ).json();
  const p = positions.items[0];
  const findings: unknown[] = [];
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of [
      "/",
      "/risk",
      `/positions/${p.store_id}/${p.product_id}`,
      "/suppliers",
      `/suppliers/${p.supplier_id}`,
      "/scenarios",
      "/methodology",
    ]) {
      await page.goto(path);
      await expect(page.locator("main h1").first()).toBeVisible();
      await expect(page.locator("main .loading")).toHaveCount(0, {
        timeout: 30000,
      });
      if (path === "/scenarios")
        await expect(
          page.getByRole("heading", {
            name: "Scenario comparison",
            exact: true,
          }),
        ).toBeVisible({ timeout: 30000 });
      const results = await new AxeBuilder({ page }).analyze();
      findings.push(
        ...results.violations
          .filter((v) => v.impact === "serious" || v.impact === "critical")
          .map((v) => ({
            width,
            path,
            id: v.id,
            nodes: v.nodes.map((n) => ({
              html: n.html,
              summary: n.failureSummary,
            })),
          })),
      );
    }
  }
  expect(findings).toEqual([]);
});
