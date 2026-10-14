import { expect, test } from "@playwright/test";

test("health page reaches the real API and PostgreSQL", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Simulated Retail Dataset")).toBeVisible();
  await page.getByText("Service health", { exact: true }).click();
  await expect(page.getByText("API: ok · Database: ok")).toBeVisible();
});
