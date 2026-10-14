// A single production-browser benchmark on the existing standard dataset.
// No data/model writes: measures 20 distinct automatic evaluations, including debounce.
import { chromium, expect } from "@playwright/test";
import { writeFileSync } from "node:fs";
import os from "node:os";
const browser = await chromium.launch({
  headless: true,
  args: ["--host-resolver-rules=MAP localhost 127.0.0.1"],
});
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });
  await page.goto("http://localhost:3000/scenarios");
  await expect(
    page.getByRole("heading", { name: "Scenario comparison", exact: true }),
  ).toBeVisible({ timeout: 30000 });
  const samples = [];
  for (let i = 0; i < 20; i++) {
    const demand = -50 + i * 5 + (i >= 10 ? 5 : 0);
    const response = page.waitForResponse(
      (r) =>
        r.url().endsWith("/scenarios/evaluate") &&
        r.request().postDataJSON().assumptions.demand_change_rate ===
          demand / 100,
    );
    const start = performance.now();
    await page
      .getByLabel("Demand change (%)", { exact: true })
      .fill(String(demand));
    const result = await response;
    if (!result.ok()) throw new Error(`Scenario failed: ${result.status()}`);
    const data = await result.json();
    const expected = data.scenario.at_risk_positions.toLocaleString("en-US");
    await expect(
      page.locator('tr[data-metric="at_risk_positions"] td').nth(2),
    ).toHaveText(expected);
    await expect(
      page.getByText("Baseline and scenario use the same as-of inputs", {
        exact: true,
      }),
    ).toBeVisible();
    samples.push({
      demand_change_rate: demand / 100,
      end_to_end_ms: performance.now() - start,
      server_computation_ms: data.computation_ms,
      positions_in_scope: data.positions_in_scope,
    });
  }
  const sorted = samples.map((s) => s.end_to_end_ms).sort((a, b) => a - b);
  const result = {
    date: "2026-10-13",
    environment: {
      os: os.platform(),
      release: os.release(),
      arch: os.arch(),
      node: process.version,
      frontend: "Next.js production build",
      browser: "Playwright Chromium",
    },
    method:
      "20 distinct full-scope automatic changes; includes input, 400 ms debounce, HTTP and rendered results; warm model cache; nearest-rank p95",
    samples,
    p50_ms: sorted[9],
    p95_ms: sorted[18],
    target_ms: 1500,
  };
  writeFileSync(
    new URL("../../docs/perf/raw/stage3_scenario.json", import.meta.url),
    JSON.stringify(result, null, 2) + "\n",
  );
  console.log(
    JSON.stringify({
      samples: samples.length,
      p50_ms: result.p50_ms,
      p95_ms: result.p95_ms,
      target_met: result.p95_ms < 1500,
    }),
  );
} finally {
  await browser.close();
}
