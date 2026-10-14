import { test, expect } from "@playwright/test";
test("all pages remain usable at desktop and mobile widths", async ({
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
  const routes = [
    ["overview", "/"],
    ["risk", "/risk"],
    ["position", `/positions/${p.store_id}/${p.product_id}`],
    ["suppliers", "/suppliers"],
    ["scenario", "/scenarios"],
    ["methodology", "/methodology"],
  ];
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  for (const width of [1440, 1280, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    for (const [name, path] of routes) {
      await page.goto(path);
      await expect(page.locator("main h1").first()).toBeVisible({
        timeout: 15000,
      });
      await expect(
        page.getByText("Simulated Retail Dataset", { exact: true }).first(),
      ).toBeAttached();
      if (name === "scenario")
        await expect(
          page.getByRole("heading", {
            name: "Scenario comparison",
            exact: true,
          }),
        ).toBeVisible({ timeout: 30000 });
      if (name === "overview")
        await expect(page.locator(".kpi dd")).toHaveCount(6);
      await expect(page.locator("main .loading")).toHaveCount(0, {
        timeout: 30000,
      });
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        )
        .toBe(true);
      if (width === 1440 || width === 390)
        await page.screenshot({
          path: `../docs/screenshots/${name}-${width}.png`,
          fullPage: true,
        });
    }
    if (width === 390) {
      await page
        .getByRole("button", { name: "Toggle navigation", exact: true })
        .click();
      await expect(
        page.getByRole("navigation", { name: "Main navigation" }),
      ).toBeVisible();
    }
  }
  expect(errors).toEqual([]);
});
