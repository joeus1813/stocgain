import { test, expect } from "@playwright/test";
test("widget failure is isolated and retry recovers real data", async ({
  page,
}) => {
  let fail = true;
  await page.route("**/api/v1/overview/top-products*", (route) =>
    fail
      ? route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "INTERNAL_ERROR",
              message: "Unable to load products.",
            },
          }),
        })
      : route.continue(),
  );
  await page.goto("/");
  const card = page.getByRole("region", {
    name: "Top at-risk products",
    exact: true,
  });
  await expect(card.getByRole("alert")).toBeVisible();
  await expect(page.locator(".kpi dd")).toHaveCount(6);
  fail = false;
  await card.getByRole("button", { name: "Retry" }).click();
  await expect(card.locator(".ranked-list a")).toHaveCount(8);
});
test("all navigation destinations and unknown route are reachable", async ({
  page,
}) => {
  await page.goto("/?store=1");
  for (const name of [
    "Risk Monitor",
    "Suppliers",
    "Scenario Lab",
    "Methodology",
    "Overview",
  ]) {
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name, exact: true })
      .click();
    await expect(page).toHaveURL(/store=1/);
    await expect(page.locator("main h1")).toBeVisible();
  }
  await page.goto("/not-an-existing-page");
  await expect(
    page.getByRole("heading", { name: "Page not found" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Back to Risk Monitor" }),
  ).toBeVisible();
});
