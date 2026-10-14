import { test, expect } from "@playwright/test";
test("supplier views drill into real delivery evidence and export matches scope", async ({
  page,
}) => {
  await page.goto("/suppliers");
  await expect(
    page.getByRole("heading", { name: "Ranked suppliers", exact: true }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(48);
  await page.locator("tbody tr").first().getByRole("link").click();
  await expect(
    page.getByRole("heading", { name: "Store lanes", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Exposed positions", exact: true }),
  ).toBeVisible();
  await page.goto("/risk?store=1");
  await expect(page.locator("tbody tr")).toHaveCount(50);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  expect((await download).suggestedFilename()).toContain(
    "stocgain_risk_positions_",
  );
});
