import { test, expect } from "@playwright/test";
test("shell persists scope, is responsive, and shows actual provenance", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/?region=1");
  await expect(page.getByLabel("Region", { exact: true })).toHaveValue("1");
  await page
    .getByText("Simulated Retail Dataset", { exact: true })
    .first()
    .click();
  await expect(page.getByText(/Seed 42/)).toBeVisible();
  await page.screenshot({ path: "../docs/screenshots/wip/phase5-1440.png" });
  await page.getByRole("link", { name: "Risk Monitor", exact: true }).click();
  await expect(page).toHaveURL(/region=1/);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await page.screenshot({ path: "../docs/screenshots/wip/phase5-1280.png" });
});
test("analytics not ready is explicit and recoverable", async ({ page }) => {
  await page.route("**/api/v1/overview/summary*", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "ANALYTICS_NOT_READY",
          message: "Analytics are not ready. Run make analytics.",
        },
      }),
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert").first()).toContainText(
    "Analytics are not ready",
  );
  await expect(
    page.getByRole("button", { name: "Retry" }).first(),
  ).toBeVisible();
});
